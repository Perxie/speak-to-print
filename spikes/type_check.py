"""Faz 0.6 — İmlecin olduğu yere yazma denemesi.

Test cümlesini, seçtiğiniz yöntemle o an etkin olan pencereye yazar:

  1. kwin-type             : metni doğrudan karakter olarak gönderir
  2. pano + Shift+Insert   : panoya koyar, Shift+Insert'e basar
  3. pano + Ctrl+V         : panoya koyar, Ctrl+V'ye basar

Her denemede: yöntemi ve hedef uygulamayı seçersiniz, geri sayım sırasında
hedef pencerede yazı alanına tıklarsınız, betik metni yazar ve sonucu sorar.
Sonuçlar spikes/data/type_check.log dosyasına da yazılır.

Çalıştırma (proje klasöründe):
  uv run python spikes/type_check.py
"""

from __future__ import annotations

import re
import secrets
import subprocess
import sys
import time
from pathlib import Path

from speak_to_print.output import OutputError, clipboard_paste, kwin_type

TEXT = "Çığ düştü; İzmir'de ılık, şöyle güzel bir gün. Deploy ettik, pull request açtım."
# Uzun dikteyi temsil eden metin: aynı cümle numaralanarak 20 kez (yaklaşık 1700 karakter).
LONG_TEXT = " ".join(f"{n}. {TEXT}" for n in range(1, 21))
LOG_FILE = Path(__file__).resolve().parent / "data" / "type_check.log"
COUNTDOWN_SECONDS = 5

METHODS = {
    "1": "kwin-type",
    "2": "pano + Shift+Insert",
    "3": "pano + Ctrl+V",
}


def log(line: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(f"[{time.strftime('%H:%M:%S')}] {line}\n")


def keyboard_layout() -> str:
    """KDE'de o an etkin olan klavye düzeni (ör. tr, us, tr(f))."""
    try:
        index = subprocess.run(["qdbus6", "org.kde.keyboard", "/Layouts", "org.kde.KeyboardLayouts.getLayout"],
                               capture_output=True, text=True, timeout=5, check=False).stdout.strip()
        layouts = subprocess.run(["qdbus6", "--literal", "org.kde.keyboard", "/Layouts",
                                  "org.kde.KeyboardLayouts.getLayoutsList"],
                                 capture_output=True, text=True, timeout=5, check=False).stdout
        names = [name + (f"({variant})" if variant else "")
                 for name, variant, _label in re.findall(r'\(sss\) "([^"]*)", "([^"]*)", "([^"]*)"', layouts)]
        return names[int(index)]
    except (IndexError, ValueError, OSError, subprocess.TimeoutExpired):
        return "bilinmiyor"


def in_klipper_history(text: str) -> bool | None:
    try:
        result = subprocess.run(["qdbus6", "org.kde.klipper", "/klipper",
                                 "org.kde.klipper.klipper.getClipboardHistoryMenu"],
                                capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return text in result.stdout if result.returncode == 0 else None


def clipboard_text() -> str:
    result = subprocess.run(["wl-paste", "--no-newline"], capture_output=True, timeout=5, check=False)
    return result.stdout.decode("utf-8", errors="replace") if result.returncode == 0 else ""


def show_difference(expected: str, actual: str) -> None:
    print(f"    beklenen: {expected}")
    print(f"    çıkan   : {actual}")
    for index, (a, b) in enumerate(zip(expected, actual)):
        if a != b:
            print(f"    ilk fark {index + 1}. karakterde: beklenen {a!r}, çıkan {b!r}")
            return
    print(f"    uzunluk farkı: beklenen {len(expected)}, çıkan {len(actual)} karakter")


def main() -> int:
    print(f"Test cümlesi:\n  {TEXT}\n")
    print(f"kwin-type: {'kurulu' if kwin_type.available() else 'BULUNAMADI'}; klavye düzeni: {keyboard_layout()}")
    pasters: dict[str, clipboard_paste.ClipboardPaster] = {}
    log("=" * 60)

    while True:
        print()
        for key, name in METHODS.items():
            print(f"  {key}) {name}")
        choice = input("Yöntem (1/2/3, çıkmak için q) > ").strip().lower()
        if choice == "q":
            break
        if choice not in METHODS:
            continue
        method = METHODS[choice]
        long = input("Metin: Enter = kısa cümle, u = uzun metin (yaklaşık 1700 karakter) > ").strip().lower() == "u"
        # Her denemeye benzersiz bir numara eklenir: böylece karşılaştırma panoda kalmış eski bir
        # kopyayla yanlışlıkla tutmaz ve pano geçmişi (Klipper) kontrolü her seferinde ölçülebilir.
        text = f"{LONG_TEXT if long else TEXT} [{secrets.randbelow(9000) + 1000}]"
        if long:
            method += " (uzun)"
        app = input("Hedef uygulamanın adı (ör. Kate, Firefox, Konsole, PyCharm) > ").strip() or "?"
        layout = keyboard_layout()

        keys = {"2": "shift+insert", "3": "ctrl+v"}.get(choice, "")
        try:
            if keys:
                if keys not in pasters:
                    print("  Sanal klavye hazırlanıyor…")
                    pasters[keys] = clipboard_paste.ClipboardPaster(keys)
            before = clipboard_text()
            in_history_before = in_klipper_history(text)

            print(f"  Yazılacak metnin sonu: …{text[-28:]}")
            print(f"  {COUNTDOWN_SECONDS} saniye içinde hedef pencerede yazı alanına tıklayın…")
            for remaining in range(COUNTDOWN_SECONDS, 0, -1):
                print(f"  {remaining}…", flush=True)
                time.sleep(1)

            start = time.perf_counter()
            if choice == "1":
                kwin_type.type_text(text)
            else:
                pasters[keys].paste(text)
            elapsed = (time.perf_counter() - start) * 1000
        except OutputError as error:
            print(f"  HATA: {error}")
            log(f"{method} | {app} | düzen {layout} | HATA: {error}")
            continue

        notes = [f"{elapsed:.0f} ms"]
        if choice != "1":
            time.sleep(0.3)
            notes.append("pano geri geldi" if clipboard_text() == before else "PANO GERİ GELMEDİ")
            history = in_klipper_history(text)
            if history is None or in_history_before is None:
                notes.append("Klipper sorgulanamadı")
            elif in_history_before:
                notes.append("Klipper'da zaten vardı (ölçülemedi)")
            else:
                notes.append("KLIPPER GEÇMİŞİNE DÜŞTÜ" if history else "Klipper geçmişine düşmedi")
        print(f"  Yazıldı ({', '.join(notes)}).")

        print("  Sonuç nasıl?")
        print("    Enter : metin doğru çıktı")
        print("    y     : yanlış, eksik ya da hiç çıkmadı")
        print("    k     : karşılaştır (önce yazılan metni seçip kopyalayın, sonra k yazın)")
        answer = input("  > ").strip().lower()
        while answer not in ("", "y", "k"):
            # Metin yanlışlıkla bu terminale yazıldıysa burada yakalanır.
            print("  Anlaşılmadı (metin bu pencereye mi yazıldı?). Yalnızca Enter, y ya da k yazın.")
            answer = input("  > ").strip().lower()
        if answer == "k":
            actual = clipboard_text().rstrip("\n ")  # bazı uygulamalar kopyalarken sona satır sonu ya da boşluk ekler
            if actual == text:
                verdict = "birebir aynı (karşılaştırıldı)"
                print("  ✓ Birebir aynı.")
            else:
                verdict = f"FARKLI (karşılaştırıldı, {len(actual)}/{len(text)} karakter): {actual[:200]!r}"
                print("  ✗ Farklı:")
                show_difference(text, actual)
        elif answer == "y":
            detail = input("  Ne oldu? (kısaca) > ").strip()
            verdict = f"YANLIŞ: {detail}"
        else:
            verdict = "doğru (gözle)"
        log(f"{method} | {app} | düzen {layout} | {', '.join(notes)} | {verdict}")

    for paster in pasters.values():
        paster.close()
    print(f"\nSonuçlar: {LOG_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
