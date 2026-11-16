"""Faz 0.4 — Model karşılaştırması.

recordings/set/ içindeki kayıtları (spikes/record_set.py ile alınır) her aday
modelle ve üç ayarla yazıya çevirir, beklenen metinle karşılaştırır:

  düz           : yalnızca language="tr"
  ipucu         : + noktalı, büyük harfli bir örnek Türkçe metin (initial_prompt).
                  "Terim sözlüğümde yok" durumunu gösterir.
  ipucu+sözlük  : + cümlelerdeki İngilizce terimlerin listesi (hotwords).
                  "Terim sözlüğümde var" durumunu, yani en iyi hâli gösterir.

Ölçütler:
  KHO  : kelime hata oranı (WER). Noktalama ve büyük/küçük harf sayılmaz.
  HHO  : harf hata oranı (CER). Türkçe ekler yüzünden KHO'dan daha adil.
  Terim: İngilizce terimlerden kaçı doğru yazıldı.
  Nokta: cümlelerden kaçı büyük harfle başlayıp . ? ! ile bitti.
  Tekrar: kaç cümlede model ilk denemesini beğenmeyip yeniden denedi
          (yeniden denenen çıktı her seferinde aynı çıkmayabilir).

Çalıştırma (proje klasöründe):
  uv run python spikes/model_compare.py
  uv run python spikes/model_compare.py --models large-v3 large-v3-turbo   # turbo'yu yeniden indirir

Rapor: recordings/set/report.md (git'e girmez).
"""

from __future__ import annotations

import argparse
import gc
import json
import re
import sys
import time
import unicodedata
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from speak_to_print.cuda_libs import preload_cuda_libraries

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SET_DIR = ROOT / "recordings" / "set"

# Aday modeller: ad → faster-whisper model adı ya da yerel klasör.
MODELS: dict[str, str] = {
    "large-v3": "large-v3",
    # Aşağıdaki ikisi elendi ve silindi (docs/model-karsilastirma.md). Varsayılan çalıştırmada
    # yer almazlar; --models ile istenirse turbo yeniden indirilir, buzzasr klasörü yoksa atlanır.
    "large-v3-turbo": "large-v3-turbo",
    "buzzasr-turkish": str(ROOT / "models" / "buzzasr-turkish-ct2"),
}

STYLE_PROMPT = ("Merhaba, bugün yaptıklarımı not alıyorum. Önce toplantıya katıldım, "
                "sonra e-postaları yanıtladım. Yarın ne yapacağıma henüz karar vermedim.")


# ---------------------------------------------------------------- metin karşılaştırma

def _strip(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[^\w\s]", "", text)  # noktalama ve kesme işaretleri gider
    return " ".join(text.split())


def normalize_tr(text: str) -> str:
    """Türkçe kurallarıyla küçük harf: İ→i, I→ı."""
    return _strip(text.replace("İ", "i").replace("I", "ı").lower())


def normalize_en(text: str) -> str:
    """İngilizce kurallarıyla küçük harf: I→i (API, GitHub gibi kelimeler için)."""
    return _strip(text.lower().replace("i̇", "i"))


def edit_distance(a: list[str] | str, b: list[str] | str) -> int:
    """Levenshtein uzaklığı: a'yı b'ye çevirmek için gereken en az ekleme/silme/değiştirme."""
    previous = list(range(len(b) + 1))
    for i, x in enumerate(a, start=1):
        current = [i]
        for j, y in enumerate(b, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (x != y)))
        previous = current
    return previous[-1]


def errors(reference: str, hypothesis: str) -> tuple[int, int, int, int]:
    """(kelime hatası, kelime sayısı, harf hatası, harf sayısı) döndürür.

    Türkçe ve İngilizce küçük harf kurallarının ikisi de denenir, az hata veren
    sayılır; böylece "API" ile "api" ya da "Ilık" ile "ılık" hata sayılmaz.
    """
    best = None
    for norm in (normalize_tr, normalize_en):
        ref, hyp = norm(reference), norm(hypothesis)
        candidate = (edit_distance(ref.split(), hyp.split()), len(ref.split()),
                     edit_distance(ref, hyp), len(ref))
        if best is None or (candidate[2], candidate[0]) < (best[2], best[0]):
            best = candidate
    assert best is not None
    return best


def dotted_i_differs(reference: str, hypothesis: str) -> bool:
    """Yalnızca Türkçe kurallarla bakınca daha çok hata çıkıyorsa İ/I/ı/i farkı olabilir."""
    ref, hyp = normalize_tr(reference), normalize_tr(hypothesis)
    return edit_distance(ref, hyp) > errors(reference, hypothesis)[2]


def level_dbfs(audio: np.ndarray) -> float:
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    return float("-inf") if peak <= 0 else 20 * float(np.log10(peak))


def term_found(term: str, hypothesis: str) -> bool:
    return any(norm(term) in norm(hypothesis) for norm in (normalize_tr, normalize_en))


def well_punctuated(text: str) -> bool:
    text = text.strip()
    return bool(text) and text[0].isupper() and text[-1] in ".?!"


# ---------------------------------------------------------------- çeviri

@dataclass
class Output:
    text: str
    seconds: float
    temperatures: list[float] = field(default_factory=list)
    no_speech_prob: float = 0.0  # modelin "konuşma yok" olasılığı (bölümlerin en yükseği)
    avg_logprob: float = 0.0  # modelin kendi metnine güveni (bölümlerin en düşüğü; 0'a yakın = emin)


def read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as wav:
        assert wav.getframerate() == 16_000 and wav.getnchannels() == 1 and wav.getsampwidth() == 2
        samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16)
    return samples.astype(np.float32) / 32768.0


def transcribe(model, audio: np.ndarray, **options) -> Output:
    start = time.perf_counter()
    segments, _info = model.transcribe(audio, language="tr", beam_size=5, vad_filter=True, **options)
    segments = list(segments)
    return Output(
        text=" ".join(s.text.strip() for s in segments),
        seconds=time.perf_counter() - start,
        temperatures=[round(s.temperature, 1) for s in segments],
        no_speech_prob=max((s.no_speech_prob for s in segments), default=0.0),
        avg_logprob=min((s.avg_logprob for s in segments), default=0.0),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Aday modelleri kullanıcının kayıtlarıyla karşılaştırır.")
    parser.add_argument("--set-dir", type=Path, default=DEFAULT_SET_DIR)
    parser.add_argument("--models", nargs="+", default=["large-v3"], choices=list(MODELS))
    args = parser.parse_args()

    manifest_path = args.set_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"Hata: {manifest_path} yok. Önce: uv run python spikes/record_set.py")
        return 1
    items = {key: value for key, value in json.loads(manifest_path.read_text(encoding="utf-8"))["items"].items()
             if (args.set_dir / f"{key}.wav").exists()}
    sentences = {k: v for k, v in items.items() if v["kind"] == "cumle"}
    specials = {k: v for k, v in items.items() if v["kind"] != "cumle"}
    audio = {key: read_wav(args.set_dir / f"{key}.wav") for key in items}
    all_terms = sorted({t for v in sentences.values() for t in v["terms"]}, key=str.lower)
    print(f"{len(sentences)} cümle, {len(specials)} özel kayıt, {len(all_terms)} farklı İngilizce terim.")

    configs: dict[str, dict] = {
        "düz": {},
        "ipucu": {"initial_prompt": STYLE_PROMPT},
        "ipucu+sözlük": {"initial_prompt": STYLE_PROMPT, "hotwords": ", ".join(all_terms)},
    }

    preload_cuda_libraries()
    from faster_whisper import WhisperModel

    # results[model][config][kayıt] = Output
    results: dict[str, dict[str, dict[str, Output]]] = {}
    for name in args.models:
        source = MODELS[name]
        if "/" in source and not Path(source).exists():
            print(f"{name}: model klasörü yok, atlanıyor ({source})")
            continue
        print(f"\n{name}: yükleniyor...", flush=True)
        model = WhisperModel(source, device="cuda", compute_type="float16")
        transcribe(model, next(iter(audio.values())))  # ısınma turu
        results[name] = {}
        for config_name, options in configs.items():
            results[name][config_name] = {key: transcribe(model, clip, **options) for key, clip in audio.items()}
            total = sum(o.seconds for o in results[name][config_name].values())
            print(f"  {config_name}: {total:.1f} sn", flush=True)
        del model
        gc.collect()  # ekran kartı belleğini sıradaki model için boşalt

    if not results:
        print("Hiç model çalıştırılamadı.")
        return 1

    # ------------------------------------------------------------ özet tablo
    lines: list[str] = ["# Model karşılaştırması", ""]
    device = next(iter(items.values())).get("device", "?")
    audio_seconds = sum(len(audio[k]) for k in sentences) / 16_000
    lines += [f"Mikrofon: {device}. {len(sentences)} cümle ({audio_seconds:.0f} sn ses), "
              f"{len(all_terms)} farklı İngilizce terim.", ""]
    lines += ["| Model | Ayar | KHO | HHO | Terim | Nokta | Tekrar | Cümlelerin süresi |", "|---|---|---|---|---|---|---|---|"]
    for name, by_config in results.items():
        for config_name, outputs in by_config.items():
            word_errors = words = char_errors = chars = hits = term_total = punctuated = retried = 0
            for key, item in sentences.items():
                we, w, ce, c = errors(item["text"], outputs[key].text)
                word_errors, words, char_errors, chars = word_errors + we, words + w, char_errors + ce, chars + c
                hits += sum(term_found(t, outputs[key].text) for t in item["terms"])
                term_total += len(item["terms"])
                punctuated += well_punctuated(outputs[key].text)
                retried += any(t > 0 for t in outputs[key].temperatures)
            seconds = sum(outputs[k].seconds for k in sentences)
            lines.append(f"| {name} | {config_name} | %{100 * word_errors / max(words, 1):.1f} "
                         f"| %{100 * char_errors / max(chars, 1):.1f} | {hits}/{term_total} "
                         f"| {punctuated}/{len(sentences)} | {retried} | {seconds:.1f} sn |")
    summary = "\n".join(lines)

    # ------------------------------------------------------------ ayrıntılar
    lines += ["", "## Cümle cümle", "",
              "Beklenen metinle (noktalama ve büyük/küçük harf dışında) aynı çıkanlar ✓ ile gösterilir.", ""]
    for key, item in sentences.items():
        lines += [f"**{key}. {item['text']}**", ""]
        for name, by_config in results.items():
            for config_name, outputs in by_config.items():
                out = outputs[key]
                word_errors, *_ = errors(item["text"], out.text)
                missing = [t for t in item["terms"] if not term_found(t, out.text)]
                mark = "✓" if word_errors == 0 else f"{word_errors} kelime hatası"
                note = f" — eksik terim: {', '.join(missing)}" if missing else ""
                if dotted_i_differs(item["text"], out.text):
                    note += " — İ/ı farkı olabilir, metne bakın"
                lines.append(f"- {name} / {config_name}: {mark}{note} — {out.text or '(boş)'}")
        lines.append("")

    titles = {"ingilizce": "Tamamı İngilizce cümle", "serbest": "Serbest konuşma",
              "uzak": "Uzaktan, kısık konuşma (uydurma metin çıkıyor mu?)", "sessizlik": "Sessizlik (boş çıkmalı)"}
    for key, item in specials.items():
        lines += [f"## {titles.get(item['kind'], key)}", ""]
        if item.get("text"):
            lines += [f"Okunan: {item['text']}", ""]
        lines += [f"Kayıt süresi: {len(audio[key]) / 16_000:.1f} sn", ""]
        for name, by_config in results.items():
            for config_name, outputs in by_config.items():
                out = outputs[key]
                retried = sum(t > 0 for t in out.temperatures)
                extra = f", {retried}/{len(out.temperatures)} bölüm yeniden denendi" if retried else ""
                if item["kind"] in ("sessizlik", "uzak") and out.text:
                    extra += f", konuşma-yok olasılığı {out.no_speech_prob:.2f}, güven {out.avg_logprob:.2f}"
                lines.append(f"- {name} / {config_name} ({out.seconds:.2f} sn{extra}): {out.text or '(boş)'}")
        lines.append("")

    # Uydurma metne karşı bir eşik seçebilmek için her kaydın ham ölçümleri.
    lines += ["## Kayıt başına ölçümler (ayar: ipucu)", "",
              "Tepe: kaydın en yüksek ses seviyesi. Konuşma-yok: modelin \"konuşma yok\" olasılığı. "
              "Güven: modelin metnine güveni (0'a yakın = emin).", ""]
    names = list(results)
    lines += ["| Kayıt | Tepe (dBFS) | " + " | ".join(f"{n}: konuşma-yok / güven" for n in names) + " |",
              "|---|---|" + "---|" * len(names)]
    for key in items:
        cells = []
        for name in names:
            out = results[name]["ipucu"][key]
            cells.append(f"{out.no_speech_prob:.2f} / {out.avg_logprob:.2f}" if out.text else "(boş)")
        lines.append(f"| {key} | {level_dbfs(audio[key]):.1f} | " + " | ".join(cells) + " |")
    lines.append("")

    report = args.set_dir / "report.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n" + summary)
    print(f"\nAyrıntılı rapor: {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
