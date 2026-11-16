"""Faz 0.4 — Model karşılaştırması için cümle kayıtları.

spikes/sentences_tr.txt içindeki cümleleri sırayla gösterir ve her birini
mikrofondan kaydeder. Sonuna dört özel kayıt ekler: tamamı İngilizce bir cümle,
45–60 saniyelik serbest konuşma, uzaktan kısık konuşma ve birkaç saniyelik sessizlik.

Kayıtlar recordings/set/ klasörüne yazılır (git'e girmez). Yarıda bırakıp
yeniden çalıştırırsanız kaldığı yerden devam eder.

Çalıştırma (proje klasöründe):
  uv run python spikes/record_set.py                     # sistem varsayılanı mikrofon
  uv run python spikes/record_set.py --device "USB PnP"  # belirli bir mikrofon
  uv run python spikes/record_set.py --redo 5            # 5 numaralı kaydı yenile
  uv run python spikes/record_set.py --status            # hangi kayıtlar var
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from PySide6.QtCore import QCoreApplication
from PySide6.QtMultimedia import QAudioDevice, QAudioFormat, QAudioSource

from mic_check import SAMPLE_RATE, dbfs, microphones, pick_device, save_wav

ROOT = Path(__file__).resolve().parent.parent
SENTENCES_FILE = Path(__file__).resolve().parent / "sentences_tr.txt"
DEFAULT_SET_DIR = ROOT / "recordings" / "set"

LEAD_IN_SECONDS = 0.7  # Bluetooth mikrofonun açılmasını beklemek için
TAIL_SECONDS = 0.3  # Enter'dan sonra son heceyi kaçırmamak için


@dataclass
class Item:
    id: str  # dosya adı: "01", "02", ..., "en", "serbest", "uzak", "sessizlik"
    kind: str  # "cumle" | "ingilizce" | "serbest" | "uzak" | "sessizlik"
    instruction: str
    text: str = ""  # beklenen metin (serbest ve sessizlikte boş)
    terms: tuple[str, ...] = ()


def load_items() -> list[Item]:
    items: list[Item] = []
    for line in SENTENCES_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        text, _, terms = line.partition("||")
        items.append(Item(
            id=f"{len(items) + 1:02d}",
            kind="cumle",
            instruction="Şu cümleyi doğal konuşma hızınızla okuyun:",
            text=text.strip(),
            terms=tuple(t.strip() for t in terms.split(",") if t.strip()),
        ))
    items.append(Item(
        id="en",
        kind="ingilizce",
        instruction="Şu İngilizce cümleyi okuyun (modelin tamamı İngilizce konuşmada ne yaptığını görmek için):",
        text="Please send me the latest version of the document before the meeting tomorrow.",
    ))
    items.append(Item(
        id="serbest",
        kind="serbest",
        instruction=("45–60 saniye boyunca aklınıza geleni anlatın (ör. dün ne yaptığınızı ya da bu projeyi). "
                     "Normalde dikte ederken konuşacağınız gibi konuşun; araya İngilizce terimler de girsin."),
    ))
    items.append(Item(
        id="uzak",
        kind="uzak",
        instruction=("Mikrofondan 2–3 metre uzaklaşın ya da başınızı çevirin ve alçak sesle bir iki cümle söyleyin. "
                     "(Model kısık seste metin uyduruyor mu, onu görmek için.)"),
    ))
    items.append(Item(
        id="sessizlik",
        kind="sessizlik",
        instruction="Hiç konuşmayın. Enter'a basın, 5 saniye kadar sessizce bekleyin, sonra yine Enter'a basın.",
    ))
    return items


def record_until_enter(app: QCoreApplication, device: QAudioDevice) -> np.ndarray:
    """Enter'a basılana kadar kayıt alır."""
    fmt = QAudioFormat()
    fmt.setSampleRate(SAMPLE_RATE)
    fmt.setChannelCount(1)
    fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)

    source = QAudioSource(device, fmt)
    io = source.start()
    chunks: list[bytes] = []

    def pump(seconds: float | None, stop: threading.Event | None = None) -> None:
        """Qt olaylarını işler ve gelen sesi toplar (süre dolana ya da stop gelene kadar)."""
        deadline = None if seconds is None else time.perf_counter() + seconds
        while True:
            app.processEvents()
            data = io.readAll().data()
            if data:
                chunks.append(bytes(data))
            if stop is not None and stop.is_set():
                return
            if deadline is not None and time.perf_counter() >= deadline:
                return
            time.sleep(0.005)

    pump(LEAD_IN_SECONDS)
    print("  ● ŞİMDİ KONUŞUN. Bitince Enter'a basın.", flush=True)

    # Enter'ı ayrı bir iş parçacığında bekliyoruz; ana iş parçacığı bu sırada
    # sesi toplamaya devam ediyor. (Java'da ayrı bir Thread + volatile bayrak gibi.)
    stop = threading.Event()
    threading.Thread(target=lambda: (sys.stdin.readline(), stop.set()), daemon=True).start()
    pump(None, stop)
    pump(TAIL_SECONDS)
    source.stop()
    return np.frombuffer(b"".join(chunks), dtype=np.int16)


def load_manifest(set_dir: Path) -> dict:
    path = set_dir / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"items": {}}


def save_manifest(set_dir: Path, manifest: dict) -> None:
    set_dir.mkdir(parents=True, exist_ok=True)
    (set_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Model karşılaştırması için cümleleri kaydeder.")
    parser.add_argument("--device", help="Mikrofon adının bir parçası (verilmezse sistem varsayılanı)")
    parser.add_argument("--set-dir", type=Path, default=DEFAULT_SET_DIR)
    parser.add_argument("--redo", action="append", default=[], help="Yeniden kaydedilecek kayıt (ör. 5, en, serbest)")
    parser.add_argument("--status", action="store_true", help="Yalnızca hangi kayıtların olduğunu göster")
    args = parser.parse_args()

    items = load_items()
    manifest = load_manifest(args.set_dir)
    redo = {r.zfill(2) if r.isdigit() else r for r in args.redo}
    unknown = redo - {item.id for item in items}
    if unknown:
        print(f"Hata: böyle bir kayıt yok: {', '.join(sorted(unknown))}")
        return 1

    def is_done(item: Item) -> bool:
        return item.id in manifest["items"] and (args.set_dir / f"{item.id}.wav").exists()

    if args.status:
        for item in items:
            print(f"  [{'x' if is_done(item) else ' '}] {item.id:>9}  {item.text or item.kind}")
        return 0

    todo = [item for item in items if item.id in redo or (not redo and not is_done(item))]
    if not todo:
        print("Bütün kayıtlar tamam. Birini yenilemek için: --redo <numara>")
        return 0

    app = QCoreApplication(sys.argv)
    device = pick_device(args.device)
    if device is None:
        print("Hata: mikrofon bulunamadı. Mevcut mikrofonlar:", ", ".join(m.description() for m in microphones()) or "(yok)")
        return 1

    print(f"Mikrofon: {device.description()}")
    print(f"{len(todo)} kayıt yapılacak. Her kayıtta: Enter'a basın, \"ŞİMDİ KONUŞUN\" yazısını görünce konuşun, bitince yine Enter'a basın.")
    print("İstediğiniz an çıkabilirsiniz (q); yeniden çalıştırınca kaldığı yerden devam eder.\n")

    for number, item in enumerate(todo, start=1):
        print(f"[{number}/{len(todo)}] ({item.id}) {item.instruction}")
        if item.text:
            print(f"\n      {item.text}\n")
        answer = input("  Enter: kaydı başlat   a: atla   q: çık > ").strip().lower()
        if answer == "q":
            break
        if answer == "a":
            print()
            continue

        while True:
            samples = record_until_enter(app, device)
            path = args.set_dir / f"{item.id}.wav"
            save_wav(path, samples)
            normalized = samples.astype(np.float32) / 32768.0
            peak = float(np.max(np.abs(normalized))) if samples.size else 0.0
            print(f"  ■ {samples.size / SAMPLE_RATE:.1f} sn kaydedildi, tepe seviye {dbfs(peak):.1f} dBFS")
            if item.kind not in ("sessizlik", "uzak") and peak < 0.05:
                print("  Uyarı: ses çok kısık görünüyor.")

            manifest["items"][item.id] = {**asdict(item), "device": device.description(),
                                          "seconds": round(samples.size / SAMPLE_RATE, 2)}
            save_manifest(args.set_dir, manifest)

            answer = input("  Enter: sonraki   t: tekrar kaydet   d: dinle > ").strip().lower()
            while answer == "d":
                subprocess.run(["pw-play", str(path)], check=False)
                answer = input("  Enter: sonraki   t: tekrar kaydet   d: dinle > ").strip().lower()
            if answer != "t":
                break
        print()

    done = sum(is_done(item) for item in items)
    print(f"{done}/{len(items)} kayıt hazır → {args.set_dir}")
    if done == len(items):
        print("Hepsi tamam. Karşılaştırma için: uv run python spikes/model_compare.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
