"""KWin pencere kuralları: KDE araçları (kwriteconfig6, qdbus6) yerine sahte bir işlev kullanılır.

Ayar klasörü geçici bir klasöre yönlendirilir; gerçek ~/.config/kwinrulesrc'ye dokunulmaz.
"""

import subprocess

import pytest

from speak_to_print import kwin_rules


@pytest.fixture
def calls(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    recorded = []

    def run(command, **kwargs):
        recorded.append((command[0], kwargs))
        return subprocess.CompletedProcess(command, 0, b"", b"")

    monkeypatch.setattr(kwin_rules.subprocess, "run", run)
    return recorded


def test_kde_tools_are_called_with_a_timeout(calls):
    kwin_rules.ensure_popup_rule("uygulama.kimligi", "Başlık", 10, 20)
    assert {tool for tool, _ in calls} == {"kwriteconfig6", "qdbus6"}
    assert all(kwargs.get("timeout") for _, kwargs in calls)


@pytest.mark.parametrize("error", [
    subprocess.TimeoutExpired(["kwriteconfig6"], 10),  # KDE aracı yanıt vermiyor
    subprocess.CalledProcessError(1, ["kwriteconfig6"]),  # KDE aracı hata verdi
])
def test_kde_tool_problems_are_reported_as_runtime_error(monkeypatch, calls, error):
    # Uygulama açılışta RuntimeError'u yakalayıp günlüğe yazar; başka bir hata türü açılışı çökertirdi.
    def run(command, **kwargs):
        raise error

    monkeypatch.setattr(kwin_rules.subprocess, "run", run)
    with pytest.raises(RuntimeError):
        kwin_rules.ensure_popup_rule("uygulama.kimligi", "Başlık", 10, 20)


def _written(calls):
    """kwriteconfig6 çağrılarından {bölüm: {anahtar: değer}}."""
    groups = {}
    for tool, kwargs, command in calls:
        if tool == "kwriteconfig6":
            group, key, value = command[4], command[6], command[7]
            groups.setdefault(group, {})[key] = value
    return groups


@pytest.fixture
def commands(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    recorded = []

    def run(command, **kwargs):
        recorded.append((command[0], kwargs, command))
        return subprocess.CompletedProcess(command, 0, b"", b"")

    monkeypatch.setattr(kwin_rules.subprocess, "run", run)
    return recorded


def test_listening_window_rule_keeps_focus_away_and_editor_rule_does_not(commands):
    kwin_rules.ensure_popup_rule("uygulama.kimligi", "Dinleme", 10, 20)
    kwin_rules.ensure_editor_rule("uygulama.kimligi", "Düzenle", 10, 5)
    groups = _written(commands)
    popup, editor = groups[kwin_rules.RULE_ID], groups[kwin_rules.EDITOR_RULE_ID]
    assert (popup["title"], popup["position"], popup["acceptfocus"]) == ("Dinleme", "10,20", "false")
    assert (editor["title"], editor["position"]) == ("Düzenle", "10,5") and "acceptfocus" not in editor
    assert popup["above"] == editor["above"] == "true"


def test_removing_one_rule_keeps_the_other(commands, tmp_path):
    (tmp_path / "kwinrulesrc").write_text(
        f"[General]\nOrder={kwin_rules.RULE_ID},{kwin_rules.EDITOR_RULE_ID},baska-kural\n\n"
        f"[{kwin_rules.RULE_ID}]\ntitle=Dinleme\n\n[{kwin_rules.EDITOR_RULE_ID}]\ntitle=Düzenle\n\n[baska-kural]\ntitle=X\n")
    assert kwin_rules.remove_popup_rule() is True
    text = (tmp_path / "kwinrulesrc").read_text()
    assert f"[{kwin_rules.RULE_ID}]" not in text and f"[{kwin_rules.EDITOR_RULE_ID}]" in text and "[baska-kural]" in text
    assert _written(commands)["General"]["Order"] == f"{kwin_rules.EDITOR_RULE_ID},baska-kural"
