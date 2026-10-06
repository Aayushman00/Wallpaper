"""Global hotkeys via RegisterHotKey — the only module touching the Win32 hotkey API."""

from __future__ import annotations

import ctypes
import logging
from collections.abc import Callable
from ctypes import wintypes

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_NOREPEAT = 0x4000

VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28

WM_QUIT = 0x0012
WM_USER = 0x0400
WM_HOTKEY = 0x0312
PM_NOREMOVE = 0x0000


class HotkeyListener:
    """Registers hotkeys and pumps messages on whichever thread calls run()."""

    def __init__(
        self,
        bindings: list[tuple[int, int, Callable[[], None]]],
        user32=None,
        kernel32=None,
    ) -> None:
        self.bindings = bindings
        self._user32 = user32
        self._kernel32 = kernel32
        self._thread_id: int | None = None

    def run(self) -> None:
        user32 = self._user32 or ctypes.windll.user32
        kernel32 = self._kernel32 or ctypes.windll.kernel32
        msg = wintypes.MSG()

        # Touching the queue first guarantees PostThreadMessage(WM_QUIT) can reach us.
        user32.PeekMessageW(ctypes.pointer(msg), None, WM_USER, WM_USER, PM_NOREMOVE)
        self._thread_id = kernel32.GetCurrentThreadId()

        registered: dict[int, Callable[[], None]] = {}
        for hotkey_id, (modifiers, vk, callback) in enumerate(self.bindings, start=1):
            if user32.RegisterHotKey(None, hotkey_id, modifiers | MOD_NOREPEAT, vk):
                registered[hotkey_id] = callback
            else:
                logging.error(
                    "Hotkey registration failed (modifiers=%#x vk=%#x); likely claimed by another app",
                    modifiers, vk,
                )

        if not registered:
            logging.error("No hotkeys registered; running in auto-generation only mode")
            return

        try:
            while user32.GetMessageW(ctypes.pointer(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY and msg.wParam in registered:
                    try:
                        registered[msg.wParam]()
                    except Exception:
                        logging.exception("Hotkey callback failed")
        finally:
            for hotkey_id in registered:
                user32.UnregisterHotKey(None, hotkey_id)

    def stop(self) -> None:
        """Ask the pump to exit. No-op if run() has not started."""
        if self._thread_id is None:
            return
        user32 = self._user32 or ctypes.windll.user32
        user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
