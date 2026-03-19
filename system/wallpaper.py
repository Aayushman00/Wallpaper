"""Wallpaper system integration."""

from __future__ import annotations

import ctypes
import platform
from pathlib import Path


class WallpaperService:
    """Applies a generated image as the Windows wallpaper."""

    def set_wallpaper(self, path: Path) -> None:
        """Set the desktop wallpaper using the Windows API."""
        if platform.system() != "Windows":
            raise OSError("Wallpaper setting only supported on Windows")
        success = ctypes.windll.user32.SystemParametersInfoW(20, 0, str(path.resolve()), 3)

        if not success:
            raise RuntimeError("SystemParametersInfoW call failed")
