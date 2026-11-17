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
