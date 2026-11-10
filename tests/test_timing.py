# -*- coding: utf-8 -*-
import random
import time

import pytest

from touch_humanization.timing import Timing


def _local(h: int, m: int = 0) -> float:
    """构造「本地时间 h:m」的 epoch，使作息窗口断言与运行时时区无关。

    直接用 epoch 0（UTC 00:00）在非 UTC 时区会落到不同本地小时，
    导致用例在 UTC+8 等环境误判。
    """
    now = time.localtime()
    return time.mktime((now.tm_year, now.tm_mon, now.tm_mday,
                        h, m, 0, 0, 0, -1))


def test_sample_lognormal_in_range():
    t = Timing(rng=random.Random(1))
    for _ in range(500):
        v = t.sample(0.6, 2.2)
        assert 0.6 <= v <= 2.2


def test_sample_lognormal_mean_correction():
    t = Timing(rng=random.Random(2))
    n = 20000
    vals = [t.sample(1.0, 5.0) for _ in range(n)]
    mean = sum(vals) / n
    # 均值校正后期望 ≈ 区间 18% 高度处的 mean（约 1.72），允许 clamp 造成偏差
    assert 1.5 <= mean <= 2.0


def test_sample_uniform():
    t = Timing(rng=random.Random(3))
    vals = [t.sample(0.5, 1.5, lognormal=False) for _ in range(2000)]
    assert all(0.5 <= v <= 1.5 for v in vals)


def test_reproducible():
    a = Timing(rng=random.Random(9))
    b = Timing(rng=random.Random(9))
    assert [a.sample(0.6, 2.2) for _ in range(20)] == \
           [b.sample(0.6, 2.2) for _ in range(20)]


def test_wake_window():
    t = Timing({"wake_window": {"start": "07:30", "end": "23:00"}},
               rng=random.Random(0))
    assert t.in_wake_window(now=_local(0, 0)) is False       # 00:00
    assert t.in_wake_window(now=_local(8, 0)) is True        # 08:00
    assert t.in_wake_window(now=_local(23, 59)) is False     # 23:59


def test_cross_midnight_window():
    t = Timing({"wake_window": {"start": "20:00", "end": "06:00"}},
               rng=random.Random(0))
    assert t.in_wake_window(now=_local(22, 0)) is True
    assert t.in_wake_window(now=_local(2, 0)) is True
    assert t.in_wake_window(now=_local(12, 0)) is False


def test_tap_cooldown_every():
    t = Timing({"cooldown_every": 3, "cooldown_seconds": 10.0},
               rng=random.Random(0))
    assert t.tap() is None
    assert t.tap() is None
    v = t.tap()
    assert v is not None and 7.0 <= v <= 13.0


def test_reseed():
    t = Timing(rng=random.Random(5))
    first = [t.sample(0.5, 2.5) for _ in range(10)]
    t.reseed(5)
    again = [t.sample(0.5, 2.5) for _ in range(10)]
    assert first == again
