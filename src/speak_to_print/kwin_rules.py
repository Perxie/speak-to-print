"""Dinleme penceresi için KWin pencere kuralı.

Wayland'de bir uygulama kendi penceresine "odak alma", "her zaman üstte dur"
ya da "ekranda şuraya yerleş" diyemez; bunlara pencere yöneticisi (KWin)
karar verir. KWin'in "pencere kuralları" (Sistem Ayarları → Pencere Yönetimi
→ Pencere Kuralları) belirli bir pencere için bu davranışları zorlamaya izin
verir. Bu modül o kurallardan birini KDE'nin ayar dosyasına yazar:

    ~/.config/kwinrulesrc      (proje dışı; bkz. docs/proje-disi-dosyalar.md)

Dosya KDE'nin kendi araçlarıyla (kreadconfig6/kwriteconfig6) okunup yazılır
ve ilk değişiklikten önce yedeği alınır.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

RULE_ID = "speak-to-print-dinleme"  # kuralın ayar dosyasındaki bölüm adı
FORCE = "2"  # KWin'de "Zorla": uygulama ne isterse istesin bu değer geçerli


def _config_path() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "kwinrulesrc"


def _read(group: str, key: str) -> str:
    """Ayar dosyasından bir değeri okur (dosyayı doğrudan ayrıştırır).

    Not: kreadconfig6, [General] bölümündeki anahtarları boş döndürdüğü için
    okuma tarafında kullanılmıyor.
    """
    config = _config_path()
    if not config.exists():
        return ""
    current = None
    for line in config.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
        elif current == group and "=" in line:
            name, _, value = line.partition("=")
            if name.strip() == key:
                return value.strip()
    return ""


def _write(group: str, key: str, value: str) -> None:
    subprocess.run(["kwriteconfig6", "--file", "kwinrulesrc", "--group", group, "--key", key, value], check=True)


def _rule_ids() -> list[str]:
    """Tanımlı kuralların kimlikleri.

    KWin 6.8 listeyi [General] Order= anahtarında tutuyor; eski sürümler
    count= ve rules= kullanıyordu (KWin eskisini yüklerken yenisine çeviriyor).
    """
    return [rule for rule in (_read("General", "Order") or _read("General", "rules")).split(",") if rule]


def _set_rule_ids(rules: list[str]) -> None:
    if _read("General", "Order") or not _read("General", "rules"):
        _write("General", "Order", ",".join(rules))
    else:
        _write("General", "count", str(len(rules)))
        _write("General", "rules", ",".join(rules))


def _reload_kwin() -> None:
    subprocess.run(["qdbus6", "org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure"],
                   capture_output=True, check=False)


def popup_rule_installed() -> bool:
    return RULE_ID in _rule_ids()


def install_popup_rule(app_id: str, title: str, x: int, y: int) -> Path | None:
    """Kuralı yazar ya da günceller. İlk seferde alınan yedeğin yolunu döndürür."""
    config = _config_path()
    backup = config.with_name(config.name + ".speak-to-print.yedek")
    made_backup = None
    if config.exists() and not backup.exists():
        shutil.copy2(config, backup)
        made_backup = backup

    settings = {
        "Description": "Speak to Print dinleme penceresi",
        # Hangi pencere: uygulama kimliği ve pencere başlığı tam eşleşmeli (1 = tam eşleşme).
        "wmclass": app_id, "wmclassmatch": "1",
        "title": title, "titlematch": "1",
        # Odak alma: tıklansa bile klavye odağı yazı yazılan pencerede kalsın.
        "acceptfocus": "false", "acceptfocusrule": FORCE,
        # Her zaman üstte ve görev çubuğu / pencere değiştiricide görünmesin.
        "above": "true", "aboverule": FORCE,
        "skiptaskbar": "true", "skiptaskbarrule": FORCE,
        "skippager": "true", "skippagerrule": FORCE,
        "skipswitcher": "true", "skipswitcherrule": FORCE,
        # Ekrandaki yeri.
        "position": f"{x},{y}", "positionrule": FORCE,
    }
    for key, value in settings.items():
        _write(RULE_ID, key, value)
    rules = _rule_ids()
    if RULE_ID not in rules:
        _set_rule_ids([*rules, RULE_ID])
    _reload_kwin()
    return made_backup


def remove_popup_rule() -> bool:
    rules = _rule_ids()
    if RULE_ID not in rules:
        return False
    _set_rule_ids([rule for rule in rules if rule != RULE_ID])
    subprocess.run(["kwriteconfig6", "--file", "kwinrulesrc", "--group", RULE_ID, "--key", "Description", "--delete"],
                   check=False)
    # Bölümün kalan anahtarlarını da temizle.
    config = _config_path()
    if config.exists():
        lines, skipping = [], False
        for line in config.read_text(encoding="utf-8").splitlines():
            if line.startswith("["):
                skipping = line.strip() == f"[{RULE_ID}]"
            if not skipping:
                lines.append(line)
        config.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
    _reload_kwin()
    return True
