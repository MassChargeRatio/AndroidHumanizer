# -*- coding: utf-8 -*-
# Humanizer facade unit tests.
# Humanizer 门面单元测试。
import time

from touch_humanization import Humanizer


def _local(h: int, m: int = 0) -> float:
    """Epoch for "local time h:m" so wake-window assertions are timezone-independent.

    构造「本地时间 h:m」的 epoch，使断言与运行时时区无关。
    """
    now = time.localtime()
    return time.mktime((now.tm_year, now.tm_mon, now.tm_mday,
                        h, m, 0, 0, 0, -1))


def test_seed_reproducible_gesture():
    # Same seed -> identical gesture.
    # 同 seed -> 轨迹一致。
    a = Humanizer(seed=123).gesture((0, 0), (500, 500))
    b = Humanizer(seed=123).gesture((0, 0), (500, 500))
    assert a.points == b.points
    assert a.intervals == b.intervals


def test_single_flow_shared_rng():
    # Sub-modules share the same rng instance.
    # 子模块共享同一个 rng 实例。
    h = Humanizer(seed=1)
    assert h.kinematics.rng is h.rng
    assert h.timing.rng is h.rng
    assert h.sensors.rng is h.rng


def test_gesture_and_timing_share_sequence():
    # The same seed reproduces the same sequence across modules.
    # 同一 seed 在不同模块调用之间复现同一序列。
    h1 = Humanizer(seed=9)
    _ = h1.gesture((0, 0), (200, 200))
    d1 = h1.timing.delay_between_actions()

    h2 = Humanizer(seed=9)
    _ = h2.gesture((0, 0), (200, 200))
    d2 = h2.timing.delay_between_actions()
    assert d1 == d2


def test_wake_window_proxy():
    # Humanizer delegates in_wake_window to Timing.
    # Humanizer 把 in_wake_window 委托给 Timing。
    h = Humanizer(seed=0)
    assert h.in_wake_window(now=_local(0, 0)) is False
    assert h.in_wake_window(now=_local(10, 0)) is True
