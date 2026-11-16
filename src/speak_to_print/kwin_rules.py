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
EDITOR_RULE_ID = "speak-to-print-duzenleme"
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


def _backup_once() -> Path | None:
    """Ayar dosyasının ilk hâlini bir kez yedekler; yedek yeni alındıysa yolunu döndürür."""
    config = _config_path()
    backup = config.with_name(config.name + ".speak-to-print.yedek")
    if config.exists() and not backup.exists():
        shutil.copy2(config, backup)
        return backup
    return None


def _install_rule(rule_id: str, description: str, app_id: str, title: str, x: int, y: int, accept_focus: bool) -> None:
    settings = {
        "Description": description,
        # Hangi pencere: uygulama kimliği ve pencere başlığı tam eşleşmeli (1 = tam eşleşme).
        "wmclass": app_id, "wmclassmatch": "1",
        "title": title, "titlematch": "1",
        # Her zaman üstte ve görev çubuğu / pencere değiştiricide görünmesin.
        "above": "true", "aboverule": FORCE,
        "skiptaskbar": "true", "skiptaskbarrule": FORCE,
        "skippager": "true", "skippagerrule": FORCE,
        "skipswitcher": "true", "skipswitcherrule": FORCE,
        # Ekrandaki yeri.
        "position": f"{x},{y}", "positionrule": FORCE,
    }
    if not accept_focus:
        # Odak alma: tıklansa bile klavye odağı yazı yazılan pencerede kalsın.
        settings |= {"acceptfocus": "false", "acceptfocusrule": FORCE}
    for key, value in settings.items():
        _write(rule_id, key, value)
    rules = _rule_ids()
    if rule_id not in rules:
        _set_rule_ids([*rules, rule_id])


def _rule_matches(rule_id: str, app_id: str, title: str, x: int, y: int, accept_focus: bool) -> bool:
    return (rule_id in _rule_ids() and _read(rule_id, "title") == title and _read(rule_id, "wmclass") == app_id
            and _read(rule_id, "position") == f"{x},{y}"
            and (_read(rule_id, "acceptfocus") == "false") == (not accept_focus))


def _remove_rule(rule_id: str) -> bool:
    rules = _rule_ids()
    if rule_id not in rules:
        return False
    _set_rule_ids([rule for rule in rules if rule != rule_id])
    config = _config_path()
    if config.exists():
        lines, skipping = [], False
        for line in config.read_text(encoding="utf-8").splitlines():
            if line.startswith("["):
                skipping = line.strip() == f"[{rule_id}]"
            if not skipping:
                lines.append(line)
        config.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
    return True


# ---------------------------------------------------------------- dinleme penceresi (odak almaz)

def popup_rule_installed() -> bool:
    return RULE_ID in _rule_ids()


def install_popup_rule(app_id: str, title: str, x: int, y: int) -> Path | None:
    """Kuralı yazar ya da günceller. İlk seferde alınan yedeğin yolunu döndürür."""
    backup = _backup_once()
    _install_rule(RULE_ID, "Speak to Print dinleme penceresi", app_id, title, x, y, accept_focus=False)
    _reload_kwin()
    return backup


def ensure_popup_rule(app_id: str, title: str, x: int, y: int) -> bool:
    """Kural yoksa ya da başlığı/konumu farklıysa yazar. Bir şey değiştiyse True döner."""
    if _rule_matches(RULE_ID, app_id, title, x, y, accept_focus=False):
        return False
    install_popup_rule(app_id, title, x, y)
    return True


def remove_popup_rule() -> bool:
    removed = _remove_rule(RULE_ID)
    if removed:
        _reload_kwin()
    return removed


# ---------------------------------------------------------------- düzenleme penceresi (odak alır)

def ensure_editor_rule(app_id: str, title: str, x: int, y: int) -> bool:
    """Düzenleme penceresini sabit bir yere ve üste koyan kural. Bu pencere odak alabilir."""
    if _rule_matches(EDITOR_RULE_ID, app_id, title, x, y, accept_focus=True):
        return False
    _backup_once()
    _install_rule(EDITOR_RULE_ID, "Speak to Print düzenleme penceresi", app_id, title, x, y, accept_focus=True)
    _reload_kwin()
    return True


def remove_editor_rule() -> bool:
    removed = _remove_rule(EDITOR_RULE_ID)
    if removed:
        _reload_kwin()
    return removed
