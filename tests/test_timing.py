# -*- coding: utf-8 -*-
# Timing unit tests.
# timing 单元测试。
import random
import time

import pytest

from android_humanizer.timing import Timing


def _local(h: int, m: int = 0) -> float:
    """Epoch for "local time h:m" so wake-window assertions are timezone-independent.

    Constructing "local time h:m" as an epoch keeps assertions independent of
    the runtime timezone. Using epoch 0 (UTC 00:00) directly lands on a
    different local hour in non-UTC zones (e.g. UTC+8) and breaks the tests.

    构造「本地时间 h:m」的 epoch，使作息窗口断言与运行时时区无关。

    直接用 epoch 0（UTC 00:00）在非 UTC 时区会落到不同本地小时，
    导致用例在 UTC+8 等环境误判。
    """
    now = time.localtime()
    return time.mktime((now.tm_year, now.tm_mon, now.tm_mday,
                        h, m, 0, 0, 0, -1))


def test_sample_lognormal_in_range():
    # All lognormal samples must stay in [lo, hi].
    # 对数正态采样必须落在 [lo, hi] 内。
    t = Timing(rng=random.Random(1))
    for _ in range(500):
        v = t.sample(0.6, 2.2)
        assert 0.6 <= v <= 2.2


def test_sample_lognormal_mean_correction():
    # After mean correction the sampled mean should be near the mid low region.
    # 均值校正后，采样均值应接近区间中低段。
    t = Timing(rng=random.Random(2))
    n = 20000
    vals = [t.sample(1.0, 5.0) for _ in range(n)]
    mean = sum(vals) / n
    # After mean correction E ~ mean at 18% of the range (~1.72); clamping adds slack.
    # 均值校正后期望 ≈ 区间 18% 高度处的 mean（约 1.72），允许 clamp 造成偏差
    assert 1.5 <= mean <= 2.0


def test_sample_uniform():
    # Uniform sampling respects bounds.
    # 均匀采样遵守区间边界。
    t = Timing(rng=random.Random(3))
    vals = [t.sample(0.5, 1.5, lognormal=False) for _ in range(2000)]
    assert all(0.5 <= v <= 1.5 for v in vals)


def test_reproducible():
    # Same seed -> identical sample sequences.
    # 同 seed -> 采样序列一致。
    a = Timing(rng=random.Random(9))
    b = Timing(rng=random.Random(9))
    assert [a.sample(0.6, 2.2) for _ in range(20)] == \
           [b.sample(0.6, 2.2) for _ in range(20)]


def test_wake_window():
    # Normal (non-cross-midnight) window.
    # 普通（非跨午夜）窗口。
    t = Timing({"wake_window": {"start": "07:30", "end": "23:00"}},
               rng=random.Random(0))
    assert t.in_wake_window(now=_local(0, 0)) is False       # 00:00
    assert t.in_wake_window(now=_local(8, 0)) is True        # 08:00
    assert t.in_wake_window(now=_local(23, 59)) is False     # 23:59


def test_cross_midnight_window():
    # Cross-midnight window (20:00 -> 06:00).
    # 跨午夜窗口（20:00 -> 06:00）。
    t = Timing({"wake_window": {"start": "20:00", "end": "06:00"}},
               rng=random.Random(0))
    assert t.in_wake_window(now=_local(22, 0)) is True
    assert t.in_wake_window(now=_local(2, 0)) is True
    assert t.in_wake_window(now=_local(12, 0)) is False


def test_tap_cooldown_every():
    # Cooldown triggers every N taps.
    # 冷却每 N 次点击触发一次。
    t = Timing({"cooldown_every": 3, "cooldown_seconds": 10.0},
               rng=random.Random(0))
    assert t.tap() is None
    assert t.tap() is None
    v = t.tap()
    assert v is not None and 7.0 <= v <= 13.0


def test_reseed():
    # reseed(seed) reproduces the initial sequence.
    # reseed(seed) 重现初始序列。
    t = Timing(rng=random.Random(5))
    first = [t.sample(0.5, 2.5) for _ in range(10)]
    t.reseed(5)
    again = [t.sample(0.5, 2.5) for _ in range(10)]
    assert first == again
