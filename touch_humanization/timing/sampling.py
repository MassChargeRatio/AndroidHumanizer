# -*- coding: utf-8 -*-
"""人类时序采样：对数正态 + 均值校正 + 作息窗口 + 冷却限流。

所有随机消费走实例级 rng，禁止全局 random.*。
"""
from __future__ import annotations

import math
import random
import time

__all__ = ["Timing"]


def _pair(v) -> tuple[float, float]:
    if isinstance(v, (list, tuple)) and len(v) >= 2:
        return float(v[0]), float(v[1])
    return 0.0, 1.0


def _to_minutes(hhmm: str) -> int:
    try:
        h, m = str(hhmm).strip().split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return 450


class Timing:
    """人类时序采样器。"""

    def __init__(self, config: dict | None = None, rng: random.Random | None = None):
        self.rng = rng or random.Random()
        c = config or {}
        self.mu_ratio = float(c.get("mu_ratio", 0.18))
        self.sigma_lo, self.sigma_hi = _pair(c.get("sigma_range", (0.45, 0.75)))
        self.delay_between = _pair(c.get("delay_between_actions", (0.6, 2.2)))
        self.delay_after_open = _pair(c.get("delay_after_open", (3.0, 6.0)))
        self.think_delay = _pair(c.get("think_delay", (1.5, 4.0)))
        self.start_jitter = _pair(c.get("start_jitter", (0, 600)))

        ww = c.get("wake_window") or {}
        self.wake_start = _to_minutes(ww.get("start", "07:30"))
        self.wake_end = _to_minutes(ww.get("end", "23:00"))

        self.cooldown_every = max(0, int(c.get("cooldown_every", 12)))
        self.cooldown_seconds = float(c.get("cooldown_seconds", 20.0))
        self.cooldown_on_captcha = float(c.get("cooldown_on_captcha", 300.0))

        self._tap_count = 0

    def sample(self, lo: float, hi: float, *, lognormal: bool = True) -> float:
        """在 [lo, hi] 内采样。lognormal=True 用均值校正的对数正态。"""
        lo, hi = sorted((lo, hi))
        if hi <= lo:
            return lo
        if not lognormal:
            return self.rng.uniform(lo, hi)
        mean = max(lo, lo + (hi - lo) * self.mu_ratio)
        sigma = self.sigma_lo + (self.sigma_hi - self.sigma_lo) * self.rng.random()
        mu = math.log(max(mean, 1e-6)) - 0.5 * sigma * sigma
        v = math.exp(self.rng.gauss(mu, sigma))
        return min(hi, max(lo, v))

    def delay_between_actions(self) -> float:
        return self.sample(*self.delay_between)

    def after_open(self) -> float:
        return self.sample(*self.delay_after_open)

    def think(self) -> float:
        return self.sample(*self.think_delay)

    def start_wait(self) -> float:
        return self.rng.uniform(*self.start_jitter)

    def in_wake_window(self, now=None) -> bool:
        t = time.localtime(now if now is not None else time.time())
        cur = t.tm_hour * 60 + t.tm_min
        if self.wake_start <= self.wake_end:
            return self.wake_start <= cur <= self.wake_end
        return cur >= self.wake_start or cur <= self.wake_end

    def tap(self) -> float | None:
        """记录一次点击；到达冷却点返回应长停的秒数，否则 None。"""
        self._tap_count += 1
        if self.cooldown_every > 0 and self._tap_count % self.cooldown_every == 0:
            return self.sample(self.cooldown_seconds * 0.7,
                               self.cooldown_seconds * 1.3,
                               lognormal=False)
        return None

    def captcha_cooldown(self) -> float:
        return self.sample(self.cooldown_on_captcha * 0.8,
                           self.cooldown_on_captcha * 1.2,
                           lognormal=False)

    def reseed(self, seed=None) -> None:
        self.rng = random.Random(seed)
        self._tap_count = 0
