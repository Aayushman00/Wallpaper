from system.hotkeys import (
    MOD_ALT, MOD_CONTROL, VK_LEFT, VK_UP, HotkeyListener,
)

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
CTRL_ALT = MOD_CONTROL | MOD_ALT


class FakeUser32:
    def __init__(self, messages=(), fail=()):
        self.messages = list(messages)   # (message, wParam), or -1 to simulate GetMessage error
        self.fail = set(fail)            # (modifiers, vk) combos RegisterHotKey rejects
        self.registered = {}
        self.unregistered = []
        self.posted = []

    def PeekMessageW(self, *args):
        return 0

    def RegisterHotKey(self, hwnd, hotkey_id, modifiers, vk):
        if (modifiers & 0x0F, vk) in self.fail:
            return 0
        self.registered[hotkey_id] = (modifiers & 0x0F, vk)
        return 1

    def GetMessageW(self, ptr, *args):
        if not self.messages:
            return 0
        item = self.messages.pop(0)
        if item == -1:
            return -1
        ptr.contents.message, ptr.contents.wParam = item
        return 1

    def UnregisterHotKey(self, hwnd, hotkey_id):
        self.unregistered.append(hotkey_id)

    def PostThreadMessageW(self, thread_id, message, wparam, lparam):
        self.posted.append((thread_id, message))


class FakeKernel32:
    def GetCurrentThreadId(self):
        return 77


def _listener(user32, calls):
    bindings = [
        (CTRL_ALT, VK_UP, lambda: calls.append("up")),
        (CTRL_ALT, VK_LEFT, lambda: calls.append("left")),
    ]
    return HotkeyListener(bindings, user32=user32, kernel32=FakeKernel32())


def test_dispatches_hotkey_messages_to_matching_callbacks():
    calls = []
    user32 = FakeUser32(messages=[(WM_HOTKEY, 2), (WM_HOTKEY, 1)])

    _listener(user32, calls).run()

    assert calls == ["left", "up"]


def test_ignores_non_hotkey_messages_and_unknown_ids():
    calls = []
    user32 = FakeUser32(messages=[(0x0100, 1), (WM_HOTKEY, 99), (WM_HOTKEY, 1)])

    _listener(user32, calls).run()

    assert calls == ["up"]


def test_failed_registration_skips_that_binding_but_keeps_others():
    calls = []
    user32 = FakeUser32(messages=[(WM_HOTKEY, 1), (WM_HOTKEY, 2)], fail=[(CTRL_ALT, VK_UP)])

    _listener(user32, calls).run()

    assert calls == ["left"]


def test_run_returns_immediately_when_nothing_registers():
    user32 = FakeUser32(messages=[(WM_HOTKEY, 1)], fail=[(CTRL_ALT, VK_UP), (CTRL_ALT, VK_LEFT)])

    _listener(user32, []).run()

    assert user32.messages == [(WM_HOTKEY, 1)]  # pump never started


def test_callback_exception_does_not_stop_the_pump():
    calls = []
    user32 = FakeUser32(messages=[(WM_HOTKEY, 1), (WM_HOTKEY, 2)])
    bindings = [
        (CTRL_ALT, VK_UP, lambda: (_ for _ in ()).throw(RuntimeError("boom"))),
        (CTRL_ALT, VK_LEFT, lambda: calls.append("left")),
    ]

    HotkeyListener(bindings, user32=user32, kernel32=FakeKernel32()).run()

    assert calls == ["left"]


def test_get_message_error_ends_the_pump_and_unregisters():
    user32 = FakeUser32(messages=[-1, (WM_HOTKEY, 1)])
    calls = []

    _listener(user32, calls).run()

    assert calls == []
    assert sorted(user32.unregistered) == [1, 2]


def test_stop_posts_quit_to_the_pump_thread_only_after_run_started():
    user32 = FakeUser32()
    listener = _listener(user32, [])

    listener.stop()
    assert user32.posted == []

    listener.run()
    listener.stop()
    assert user32.posted == [(77, WM_QUIT)]
