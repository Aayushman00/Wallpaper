"""Detect a fullscreen foreground app so generation can defer around games/videos."""

from __future__ import annotations

import ctypes
import logging
from ctypes import wintypes

SM_CXSCREEN = 0
SM_CYSCREEN = 1
GWL_STYLE = -16
WS_CAPTION = 0x00C00000
DESKTOP_CLASSES = ("Progman", "WorkerW")


def is_fullscreen_app_active(user32=None) -> bool:
    """True if the foreground window covers the whole primary screen.

    Fails open: any API problem returns False so generation is never blocked forever.
    """
    try:
        user32 = user32 or ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        # The desktop/shell window spans the screen too; it is not an app to defer for.
        if not hwnd or hwnd in (user32.GetDesktopWindow(), user32.GetShellWindow()):
            return False

        # Win+D / re-parented icons make a full-screen WorkerW the foreground window.
        class_name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_name, 256)
        if class_name.value in DESKTOP_CLASSES:
            return False

        # Maximized apps (esp. with an auto-hide taskbar) span the screen but keep a caption;
        # real fullscreen/borderless games do not.
        if (user32.GetWindowLongW(hwnd, GWL_STYLE) & WS_CAPTION) == WS_CAPTION:
            return False

        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.pointer(rect)):
            return False

        return (
            rect.left <= 0
            and rect.top <= 0
            and rect.right >= user32.GetSystemMetrics(SM_CXSCREEN)
            and rect.bottom >= user32.GetSystemMetrics(SM_CYSCREEN)
        )
    except Exception:
        logging.exception("Fullscreen check failed, treating as not fullscreen")
        return False
