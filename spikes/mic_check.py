"""Faz 0.3 — Mikrofon denemesi.

Ne yapar?
  1. QtMultimedia'nın gördüğü mikrofonları listeler (KDE'deki adlarıyla).
  2. Enter'a basılınca seçilen mikrofondan 16 kHz mono kayıt alır.
     Mikrofon, gerçek uygulamadaki gibi tam o anda açılır; böylece ilk
     kelimenin kesilip kesilmediği görülür.
  3. Kaydı spikes/data/ altına WAV olarak yazar, ses seviyesini ve
     mikrofonun açılma gecikmesini raporlar.
  4. Kaydı Whisper ile (Türkçe) yazıya çevirir.

Çalıştırma (proje klasöründe):
  uv run python spikes/mic_check.py                  # sistem varsayılanı, 8 sn
  uv run python spikes/mic_check.py --list           # yalnızca listele
  uv run python spikes/mic_check.py --device "USB PnP" --seconds 10
  uv run python spikes/mic_check.py --no-transcribe  # yazıya çevirme
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PySide6.QtCore import QCoreApplication, QTimer
from PySide6.QtMultimedia import QAudioDevice, QAudioFormat, QAudioSource, QMediaDevices

DATA_DIR = Path(__file__).resolve().parent / "data"  # git'e girmez (.gitignore)
SAMPLE_RATE = 16_000  # Whisper 16 kHz mono ses bekler


def device_id(device: QAudioDevice) -> str:
    return bytes(device.id().data()).decode(errors="replace")


def is_monitor(device: QAudioDevice) -> bool:
    """Hoparlöre giden sesin kopyası olan 'monitor' kaynakları mikrofon değildir."""
    return device_id(device).endswith(".monitor")


def microphones() -> list[QAudioDevice]:
    return [d for d in QMediaDevices.audioInputs() if not is_monitor(d)]


def pick_device(name: str | None) -> QAudioDevice | None:
    if name is None:
        default = QMediaDevices.defaultAudioInput()
        return None if default.isNull() or is_monitor(default) else default
    matches = [d for d in microphones() if name.lower() in d.description().lower()]
    return matches[0] if matches else None


def dbfs(value: float) -> float:
    """Genliği (0..1) desibele çevirir; 0 dBFS en yüksek ses, -inf tam sessizlik."""
    return float("-inf") if value <= 0 else 20 * np.log10(value)


def source_state(device: QAudioDevice) -> str:
    """Kaynağın PipeWire'daki durumu (SUSPENDED = uykuda, RUNNING = açık)."""
    result = subprocess.run(["pactl", "list", "short", "sources"], capture_output=True, text=True, check=False)
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 5 and parts[1] == device_id(device):
            return parts[-1]
    return "bilinmiyor"


def speech_onset_ms(samples: np.ndarray) -> float | None:
    """Sesin gürültü tabanının belirgin biçimde üstüne ilk çıktığı an (ms)."""
    frame = SAMPLE_RATE // 100  # 10 ms'lik dilimler
    count = samples.size // frame
    if count < 10:
        return None
    frames = samples[: count * frame].astype(np.float32).reshape(count, frame) / 32768.0
    levels = np.sqrt(np.mean(frames**2, axis=1))
    noise = float(np.percentile(levels, 10))
    threshold = max(noise * 8, 0.01)  # gürültünün 8 katı ve en az -40 dBFS
    loud = np.flatnonzero(levels > threshold)
    return float(loud[0] * 10) if loud.size else None


@dataclass
class Recording:
    samples: np.ndarray
    start_ms: float  # Enter'dan start() dönene kadar
    first_chunk_ms: float  # Enter'dan ilk ses paketine kadar
    first_chunk_audio_ms: float  # ilk paketteki sesin uzunluğu
    last_chunk_before_stop_ms: float  # son paketin kayıt bitiminden ne kadar önce geldiği


def record(app: QCoreApplication, device: QAudioDevice, seconds: float, pressed_at: float) -> Recording:
    """Kayıt alır. `pressed_at`, kullanıcının Enter'a bastığı andır."""
    fmt = QAudioFormat()
    fmt.setSampleRate(SAMPLE_RATE)
    fmt.setChannelCount(1)
    fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
    if not device.isFormatSupported(fmt):
        raise RuntimeError("Bu mikrofon 16 kHz mono 16 bit kaydı desteklemiyor.")

    chunks: list[bytes] = []
    chunk_times: list[float] = []

    source = QAudioSource(device, fmt)
    io = source.start()  # mikrofon tam burada açılır
    started_at = time.perf_counter()

    def on_ready() -> None:
        data = io.readAll().data()
        if data:
            chunk_times.append(time.perf_counter())
            chunks.append(bytes(data))

    # Qt sinyali: Java'daki listener gibi; veri geldikçe on_ready çağrılır.
    io.readyRead.connect(on_ready)
    QTimer.singleShot(int(seconds * 1000), app.quit)
    app.exec()  # olay döngüsü; kayıt süresi dolunca quit() ile çıkar
    stopped_at = time.perf_counter()
    on_ready()
    error = source.error().name
    source.stop()
    if error != "NoError":
        raise RuntimeError(f"Kayıt hatası: {error}")

    samples = np.frombuffer(b"".join(chunks), dtype=np.int16)
    nan = float("nan")
    return Recording(
        samples=samples,
        start_ms=(started_at - pressed_at) * 1000,
        first_chunk_ms=(chunk_times[0] - pressed_at) * 1000 if chunk_times else nan,
        first_chunk_audio_ms=len(chunks[0]) / 2 / SAMPLE_RATE * 1000 if chunks else nan,
        last_chunk_before_stop_ms=(stopped_at - chunk_times[-1]) * 1000 if chunk_times else nan,
    )


def save_wav(path: Path, samples: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(samples.tobytes())


def transcribe(samples: np.ndarray, model_name: str) -> tuple[str, float]:
    from speak_to_print.cuda_libs import preload_cuda_libraries

    preload_cuda_libraries()
    from faster_whisper import WhisperModel

    model = WhisperModel(model_name, device="cuda", compute_type="float16")
    audio = samples.astype(np.float32) / 32768.0
    start = time.perf_counter()
    segments, _info = model.transcribe(audio, language="tr", beam_size=5, vad_filter=True)
    text = " ".join(segment.text.strip() for segment in segments)
    return text, time.perf_counter() - start


def main() -> int:
    parser = argparse.ArgumentParser(description="Mikrofonu dener: kayıt alır, seviyeyi ölçer, yazıya çevirir.")
    parser.add_argument("--list", action="store_true", help="Yalnızca mikrofonları listele")
    parser.add_argument("--device", help="Mikrofon adının bir parçası (verilmezse sistem varsayılanı)")
    parser.add_argument("--seconds", type=float, default=8.0, help="Kayıt süresi")
    parser.add_argument("--model", default="large-v3")
    parser.add_argument("--no-transcribe", action="store_true", help="Kaydı yazıya çevirme")
    parser.add_argument("--no-wait", action="store_true", help="Enter beklemeden hemen kaydet")
    args = parser.parse_args()

    app = QCoreApplication(sys.argv)  # QtMultimedia bir Qt uygulama nesnesi ister

    mics = microphones()
    default = QMediaDevices.defaultAudioInput()
    print("Mikrofonlar:")
    for mic in mics:
        mark = "  (sistem varsayılanı)" if mic.id() == default.id() else ""
        print(f"  - {mic.description()}{mark}")
    if not mics:
        print("  (hiç mikrofon bulunamadı)")
    if not default.isNull() and is_monitor(default):
        print("Uyarı: sistemin varsayılan kaynağı bir monitor (hoparlör sesi), mikrofon değil.")
    if args.list:
        return 0

    device = pick_device(args.device)
    if device is None:
        print("Hata: kullanılacak mikrofon bulunamadı." if args.device is None
              else f"Hata: adında '{args.device}' geçen bir mikrofon yok.")
        return 1

    print(f"\nKullanılacak mikrofon: {device.description()}")
    print(f"Mikrofonun kayıttan önceki durumu: {source_state(device)}")
    if not args.no_wait:
        input(f"Enter'a basın ve HEMEN konuşmaya başlayın ({args.seconds:.0f} sn kayıt)... ")
    pressed_at = time.perf_counter()
    print("● Kayıt başladı, konuşun.")
    rec = record(app, device, args.seconds, pressed_at)
    samples = rec.samples
    print("■ Kayıt bitti.")

    if samples.size == 0:
        print("Hata: mikrofondan hiç ses verisi gelmedi.")
        return 1

    safe_name = "".join(c if c.isalnum() else "_" for c in device.description()).strip("_")
    path = DATA_DIR / f"mic_{safe_name}_{time.strftime('%H%M%S')}.wav"
    save_wav(path, samples)

    normalized = samples.astype(np.float32) / 32768.0
    peak = float(np.max(np.abs(normalized)))
    rms = float(np.sqrt(np.mean(normalized**2)))
    clipped = int(np.sum(np.abs(samples) >= 32767))

    print("\n=== Özet ===")
    print(f"Kayıt: {samples.size / SAMPLE_RATE:.2f} sn (istenen {args.seconds:.1f} sn) → {path}")
    print(f"Enter'dan sonra: mikrofon {rec.start_ms:.0f} ms'de açıldı, ilk ses paketi {rec.first_chunk_ms:.0f} ms'de geldi "
          f"({rec.first_chunk_audio_ms:.0f} ms ses içeriyor); son paket bitişten {rec.last_chunk_before_stop_ms:.0f} ms önce geldi")
    onset = speech_onset_ms(samples)
    print("Kayıtta ilk belirgin ses: " + (f"{onset:.0f} ms" if onset is not None else "bulunamadı (sessiz kayıt)"))
    print(f"Ses seviyesi: tepe {dbfs(peak):.1f} dBFS, ortalama {dbfs(rms):.1f} dBFS, kırpılan örnek {clipped}")
    if peak < 0.02:
        print("Uyarı: kayıt neredeyse sessiz. Mikrofon kapalı ya da sesi çok kısık olabilir.")
    elif clipped > 50:
        print("Uyarı: ses çok yüksek, kırpılıyor. Mikrofon seviyesini biraz düşürün.")
    print(f"Dinlemek için: pw-play {path}")

    if not args.no_transcribe:
        print(f"\nYazıya çevriliyor ({args.model}, Türkçe)...")
        text, seconds = transcribe(samples, args.model)
        print(f"Metin ({seconds:.2f} sn): {text or '(boş)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
