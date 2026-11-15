"""Faz 0.2 — GPU denemesi.

Ne yapar?
  1. pip ile gelen CUDA kütüphanelerini yükler (LD_LIBRARY_PATH gerekmeden).
  2. Whisper modelini indirir (ilk seferde birkaç GB, ~/.cache/huggingface).
  3. Modeli ekran kartına yükler ve yükleme süresini ölçer.
  4. Örnek bir kaydı (JFK konuşması, ~11 sn, İngilizce) ve onun 5 kez arka
     arkaya eklenmiş uzun hâlini birkaç kez çevirip hızı ölçer.
  5. Modelin kullandığı ekran kartı belleğini nvidia-smi'den okur.

Çalıştırma (proje klasöründe):
  uv run python spikes/gpu_check.py
  uv run python spikes/gpu_check.py --model large-v3-turbo
  uv run python spikes/gpu_check.py --audio kayit.wav --language tr
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np

from speak_to_print.cuda_libs import preload_cuda_libraries

SAMPLE_URL = "https://github.com/SYSTRAN/faster-whisper/raw/master/tests/data/jfk.flac"
DATA_DIR = Path(__file__).resolve().parent / "data"  # git'e girmez (.gitignore)
SAMPLE_RATE = 16_000  # Whisper 16 kHz mono ses bekler
MIN_SPEED = 5.0  # Geçme ölçütü: gerçek zamanın en az 5 katı hız


def ensure_sample() -> Path:
    path = DATA_DIR / "jfk.flac"
    if not path.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Örnek ses indiriliyor: {SAMPLE_URL}")
        urllib.request.urlretrieve(SAMPLE_URL, path)
    return path


def gpu_memory_mib(pid: int) -> int | None:
    """Bu sürecin ekran kartında kullandığı belleği (MiB) nvidia-smi'den okur."""
    result = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True,
        check=False,
    )
    for line in result.stdout.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 2 and parts[0] == str(pid) and parts[1].isdigit():
            return int(parts[1])
    return None


def transcribe(model, audio: np.ndarray, language: str) -> tuple[str, float]:
    start = time.perf_counter()
    segments, _info = model.transcribe(audio, language=language, beam_size=5, vad_filter=True)
    # `segments` bir jeneratör (Java'daki tembel Stream gibi): çeviri, biz
    # elemanları tükettikçe yapılır. Süreyi doğru ölçmek için hepsini tüketiyoruz.
    text = " ".join(segment.text.strip() for segment in segments)
    return text, time.perf_counter() - start


def main() -> int:
    parser = argparse.ArgumentParser(description="Whisper modelini GPU'da dener ve hızını ölçer.")
    parser.add_argument("--model", default="large-v3", help="Model adı ya da Hugging Face deposu")
    parser.add_argument("--compute-type", default="float16")
    parser.add_argument("--audio", type=Path, help="Denenecek ses dosyası (verilmezse JFK örneği)")
    parser.add_argument("--language", help="Konuşma dili (varsayılan: örnek için en, dosya için tr)")
    parser.add_argument("--runs", type=int, default=3, help="Her kayıt kaç kez çevrilsin")
    args = parser.parse_args()
    language = args.language or ("tr" if args.audio else "en")

    print(f"LD_LIBRARY_PATH: {os.environ.get('LD_LIBRARY_PATH') or '(ayarlı değil)'}")
    loaded = preload_cuda_libraries()
    print("Önceden yüklenen CUDA kütüphaneleri:", ", ".join(p.name for p in loaded) or "(yok)")

    from faster_whisper import WhisperModel, decode_audio, download_model

    start = time.perf_counter()
    model_path = download_model(args.model)
    print(f"Model hazır ({time.perf_counter() - start:.1f} sn, indirme dahil): {model_path}")

    start = time.perf_counter()
    model = WhisperModel(model_path, device="cuda", compute_type=args.compute_type)
    load_seconds = time.perf_counter() - start
    print(f"Model ekran kartına yüklendi: {load_seconds:.1f} sn ({args.compute_type})")
    vram_after_load = gpu_memory_mib(os.getpid())

    audio_path = args.audio or ensure_sample()
    short = decode_audio(str(audio_path), sampling_rate=SAMPLE_RATE)
    gap = np.zeros(SAMPLE_RATE // 2, dtype=short.dtype)
    long = np.concatenate([np.concatenate([short, gap])] * 5)

    print("\nIsınma turu (ilk çeviri CUDA'yı da hazırlar, ölçüme katılmaz)...")
    text, seconds = transcribe(model, short, language)
    print(f"  {seconds:.2f} sn — metin: {text}")

    results = []
    for name, clip in (("kısa", short), ("uzun", long)):
        duration = len(clip) / SAMPLE_RATE
        times = [transcribe(model, clip, language)[1] for _ in range(args.runs)]
        best = min(times)
        results.append((name, duration, best, duration / best))
        print(f"  {name} kayıt ({duration:.1f} sn): en iyi {best:.2f} sn, "
              f"tümü {', '.join(f'{t:.2f}' for t in times)}")

    vram_peak = gpu_memory_mib(os.getpid())

    print("\n=== Özet ===")
    print(f"Model: {args.model} ({args.compute_type}), yükleme {load_seconds:.1f} sn")
    print(f"Ekran kartı belleği: yükleme sonrası {vram_after_load} MiB, çeviriden sonra {vram_peak} MiB")
    for name, duration, best, speed in results:
        print(f"{name} kayıt: {duration:.1f} sn ses {best:.2f} sn'de çevrildi → gerçek zamanın {speed:.0f} katı")
    if not args.audio:
        print("Not: uzun kayıt aynı cümlenin 5 tekrarı. Whisper bu tekrarı 'takılma' sayıp çeviriyi "
              "yeniden denediği için yavaş çıkıyor; bu kayıt uzun gerçek konuşmayı temsil etmez.")
    passed = all(speed >= MIN_SPEED for *_, speed in results)
    print(f"Sonuç: {'GEÇTİ' if passed else 'KALDI'} (ölçüt: gerçek zamanın en az {MIN_SPEED:.0f} katı)")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
