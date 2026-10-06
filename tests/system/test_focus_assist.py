from system.focus_assist import is_fullscreen_app_active

DESKTOP, SHELL = 100, 200


class FakeUser32:
    def __init__(self, hwnd=1, rect=(0, 0, 1920, 1080), screen=(1920, 1080), rect_ok=1, explode=False):
        self.hwnd, self.rect, self.screen, self.rect_ok, self.explode = hwnd, rect, screen, rect_ok, explode

    def GetForegroundWindow(self):
        if self.explode:
            raise OSError("boom")
        return self.hwnd

    def GetDesktopWindow(self):
        return DESKTOP

    def GetShellWindow(self):
        return SHELL

    def GetWindowRect(self, hwnd, rect_ptr):
        left, top, right, bottom = self.rect
        rect_ptr.contents.left, rect_ptr.contents.top = left, top
        rect_ptr.contents.right, rect_ptr.contents.bottom = right, bottom
        return self.rect_ok

    def GetSystemMetrics(self, index):
        return self.screen[index]  # SM_CXSCREEN=0, SM_CYSCREEN=1


def test_fullscreen_window_is_detected():
    assert is_fullscreen_app_active(FakeUser32()) is True


def test_borderless_overscan_window_counts_as_fullscreen():
    assert is_fullscreen_app_active(FakeUser32(rect=(-8, -8, 1928, 1088))) is True


def test_windowed_or_taskbar_clipped_window_is_not_fullscreen():
    assert is_fullscreen_app_active(FakeUser32(rect=(100, 100, 900, 700))) is False
    assert is_fullscreen_app_active(FakeUser32(rect=(0, 0, 1920, 1040))) is False


def test_desktop_or_shell_focus_is_not_fullscreen():
    assert is_fullscreen_app_active(FakeUser32(hwnd=DESKTOP)) is False
    assert is_fullscreen_app_active(FakeUser32(hwnd=SHELL)) is False


def test_no_foreground_window_is_not_fullscreen():
    assert is_fullscreen_app_active(FakeUser32(hwnd=0)) is False


def test_failed_get_window_rect_fails_open():
    assert is_fullscreen_app_active(FakeUser32(rect_ok=0)) is False


def test_api_exception_fails_open():
    assert is_fullscreen_app_active(FakeUser32(explode=True)) is False
