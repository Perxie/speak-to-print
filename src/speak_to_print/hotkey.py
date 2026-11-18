"""Global kısayol: XDG GlobalShortcuts portalı (KDE Plasma Wayland).

Wayland'de bir uygulama klavyeyi kendisi dinleyemez. Kısayolu masaüstü (KDE)
tutar ve basıldığında bize D-Bus üzerinden haber verir. Akış:

  1. Registry.Register   : "ben şu .desktop dosyasındaki uygulamayım" der.
                           İlk portal çağrısından ÖNCE yapılmalıdır.
  2. CreateSession       : kısayollar için bir oturum açar.
  3. BindShortcuts       : kısayolları bildirir. İlk seferde KDE kullanıcıya
                           bir onay penceresi gösterir.
  4. Activated/Deactivated sinyalleri: tuşa basıldı / tuş bırakıldı.

D-Bus istemcisi (dbus-fast) asyncio ile çalışır. asyncio, Python'un tek iş
parçacıklı olay döngüsüdür (Java'daki CompletableFuture zincirlerine benzer).
Qt'nin kendi olay döngüsüyle çakışmasın diye ayrı bir iş parçacığında koşar;
sonuçlar Qt sinyalleriyle ana iş parçacığına aktarılır (Swing'deki
invokeLater gibi: sinyal, alıcının iş parçacığında işlenir).
"""

from __future__ import annotations

import asyncio
import secrets
import threading
from dataclasses import dataclass

from dbus_fast import BusType, Message, MessageType, Variant
from dbus_fast.aio import MessageBus
from PySide6.QtCore import QObject, Signal

PORTAL_NAME = "org.freedesktop.portal.Desktop"
PORTAL_PATH = "/org/freedesktop/portal/desktop"
REGISTRY_IFACE = "org.freedesktop.host.portal.Registry"
SHORTCUTS_IFACE = "org.freedesktop.portal.GlobalShortcuts"
REQUEST_IFACE = "org.freedesktop.portal.Request"

REQUEST_TIMEOUT_SECONDS = 300  # onay penceresi açıkken kullanıcıyı bekleriz


@dataclass(frozen=True)
class Shortcut:
    id: str  # sinyallerde geri gelen ad, ör. "dictate"
    description: str  # KDE'nin kısayol ayarlarında görünen açıklama


class PortalError(RuntimeError):
    pass


class PortalHotkeys(QObject):
    """Portal kısayollarını dinler ve Qt sinyali olarak yayar."""

    activated = Signal(str)  # kısayol kimliği: tuşa basıldı
    deactivated = Signal(str)  # kısayol kimliği: tuş bırakıldı
    bound = Signal(dict)  # {kısayol kimliği: tuş açıklaması}; kısayollar hazır ya da değişti
    failed = Signal(str)  # hata açıklaması

    def __init__(self, app_id: str, shortcuts: list[Shortcut], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._app_id = app_id
        self._shortcuts = shortcuts
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop: asyncio.Event | None = None
        self._bus: MessageBus | None = None
        self._session: str | None = None

    # ------------------------------------------------------------ dışa açık

    def start(self) -> None:
        """Dinlemeyi arka plan iş parçacığında başlatır."""
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._thread_main, name="portal-hotkeys", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Dinlemeyi durdurur ve iş parçacığının bitmesini bekler."""
        if self._loop is not None and self._stop is not None:
            self._loop.call_soon_threadsafe(self._stop.set)
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def configure(self) -> None:
        """KDE'nin bu uygulama için kısayol ayar penceresini açar."""
        if self._loop is not None:
            asyncio.run_coroutine_threadsafe(self._configure(), self._loop)

    # ------------------------------------------------------------ iş parçacığı

    def _thread_main(self) -> None:
        try:
            asyncio.run(self._main())
        except Exception as error:  # noqa: BLE001 — hatayı arayüze taşımak için hepsini yakalıyoruz
            self.failed.emit(f"{type(error).__name__}: {error}")

    async def _main(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._stop = asyncio.Event()
        bus = self._bus = await MessageBus(bus_type=BusType.SESSION).connect()
        try:
            # 1. Kimliğimizi bildir (ilk portal çağrısından önce).
            await self._call(REGISTRY_IFACE, "Register", "sa{sv}", [self._app_id, {}])

            # 2. Oturum aç.
            session_token = "stp_" + secrets.token_hex(8)
            results = await self._request(
                "CreateSession", "a{sv}",
                lambda token: [{"handle_token": Variant("s", token),
                                "session_handle_token": Variant("s", session_token)}],
            )
            self._session = results["session_handle"].value

            # 3. Sinyalleri dinlemeye başla (bağlamadan önce, hiçbirini kaçırmamak için).
            await self._add_match(f"type='signal',sender='{PORTAL_NAME}',interface='{SHORTCUTS_IFACE}'")
            bus.add_message_handler(self._on_message)

            # 4. Kısayolları bildir. İlk seferde KDE onay penceresi açar.
            shortcuts = [
                [s.id, {"description": Variant("s", s.description)}]
                for s in self._shortcuts
            ]
            results = await self._request(
                "BindShortcuts", "oa(sa{sv})sa{sv}",
                lambda token: [self._session, shortcuts, "", {"handle_token": Variant("s", token)}],
            )
            self.bound.emit(_triggers(results.get("shortcuts")))

            await self._stop.wait()
        finally:
            bus.disconnect()

    async def _configure(self) -> None:
        try:
            await self._call(SHORTCUTS_IFACE, "ConfigureShortcuts", "osa{sv}", [self._session, "", {}])
        except Exception as error:  # noqa: BLE001
            self.failed.emit(f"Kısayol ayarları açılamadı: {error}")

    # ------------------------------------------------------------ D-Bus yardımcıları

    async def _call(self, interface: str, member: str, signature: str, body: list) -> list:
        assert self._bus is not None
        reply = await self._bus.call(Message(
            destination=PORTAL_NAME, path=PORTAL_PATH, interface=interface,
            member=member, signature=signature, body=body,
        ))
        assert reply is not None
        if reply.message_type == MessageType.ERROR:
            raise PortalError(f"{interface}.{member}: {reply.error_name}: {' '.join(map(str, reply.body))}")
        return reply.body

    async def _add_match(self, rule: str) -> None:
        assert self._bus is not None
        await self._bus.call(Message(
            destination="org.freedesktop.DBus", path="/org/freedesktop/DBus",
            interface="org.freedesktop.DBus", member="AddMatch", signature="s", body=[rule],
        ))

    async def _request(self, member: str, signature: str, make_body) -> dict:
        """Portalın "istek" kalıbı: yöntem hemen döner, asıl sonuç Response sinyaliyle gelir.

        Sinyali kaçırmamak için, isteğin yolunu önceden hesaplayıp yöntemi
        çağırmadan önce dinlemeye başlıyoruz.
        """
        assert self._bus is not None and self._loop is not None
        bus = self._bus
        token = "stp_" + secrets.token_hex(8)
        sender = bus.unique_name.lstrip(":").replace(".", "_")
        path = f"{PORTAL_PATH}/request/{sender}/{token}"
        future: asyncio.Future = self._loop.create_future()

        def handler(message: Message) -> None:
            if (message.message_type == MessageType.SIGNAL and message.interface == REQUEST_IFACE
                    and message.member == "Response" and message.path == path and not future.done()):
                future.set_result(message.body)

        await self._add_match(f"type='signal',sender='{PORTAL_NAME}',interface='{REQUEST_IFACE}',path='{path}'")
        bus.add_message_handler(handler)
        try:
            await self._call(SHORTCUTS_IFACE, member, signature, make_body(token))
            code, results = await asyncio.wait_for(future, REQUEST_TIMEOUT_SECONDS)
        finally:
            bus.remove_message_handler(handler)
        if code == 1:
            raise PortalError(f"{member}: kullanıcı iptal etti.")
        if code != 0:
            raise PortalError(f"{member}: portal isteği reddetti (kod {code}).")
        return results

    def _on_message(self, message: Message) -> None:
        if message.message_type != MessageType.SIGNAL or message.interface != SHORTCUTS_IFACE:
            return
        if not message.body or message.body[0] != self._session:
            return
        if message.member == "Activated":
            self.activated.emit(message.body[1])
        elif message.member == "Deactivated":
            self.deactivated.emit(message.body[1])
        elif message.member == "ShortcutsChanged":
            self.bound.emit(_triggers(message.body[1]))


def _triggers(shortcuts) -> dict[str, str]:
    """Portalın a(sa{sv}) listesini {kimlik: tuş açıklaması} sözlüğüne çevirir.

    Yanıtın biçimi beklenenden farklıysa hata vermez; kısayol yine çalışır,
    yalnızca tuşun adı gösterilemez.
    """
    result: dict[str, str] = {}
    try:
        value = shortcuts.value if isinstance(shortcuts, Variant) else (shortcuts or [])
        for shortcut_id, properties in value:
            trigger = properties.get("trigger_description")
            result[str(shortcut_id)] = str(trigger.value if isinstance(trigger, Variant) else trigger or "")
    except Exception:  # noqa: BLE001
        result.setdefault("?", repr(shortcuts))
    return result
