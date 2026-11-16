"""speak-to-print: KDE Plasma (Wayland) için yerel dikte uygulaması."""


def main() -> int:
    # Ağır kütüphaneler (Qt, model) yalnızca uygulama gerçekten başlatılırken içe aktarılır.
    from .app import main as run

    return run()
