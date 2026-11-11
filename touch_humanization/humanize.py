# -*- coding: utf-8 -*-
"""Humanizer facade: a single random stream shared by kinematics / timing / sensors.

Humanizer 门面：单一随机流贯穿 kinematics / timing / sensors。
"""
from __future__ import annotations

import random
import time

from .config import merge_config
from .kinematics import Gesture, Kinematics
from .sensors import Sensors
from .timing import Timing

__all__ = ["Humanizer", "Gesture"]


class Humanizer:
    """Humanization facade.

    - When a seed is given, one internal `random.Random` is created and shared
      by all three sub-modules (single stream).
    - When no seed is given, an instance-local stream is still created so the
      global `random` module is never touched.
    - Each sub-module can also be used standalone (each holding its own rng).

    Humanizer 门面：

    - 传 seed 时内部创建一个 `random.Random`，三个子模块共享它（单一流）。
    - 不传 seed 时同样创建实例流，不污染全局 `random`。
    - 三个子模块也可单独使用（各自持有实例 rng）。
    """

    def __init__(self, config: dict | None = None, seed: int | None = None):
        self.config = merge_config(config)
        self.rng = random.Random(seed)
        self.kinematics = Kinematics(self.config["kinematics"], rng=self.rng)
        self.timing = Timing(self.config["timing"], rng=self.rng)
        self.sensors = Sensors(self.config["sensors"], rng=self.rng)

    def gesture(self, start, end, *, for_slider: bool = False,
                exact_end: bool = True) -> Gesture:
        # Delegate to kinematics.
        # 委托给 kinematics 生成轨迹。
        return self.kinematics.generate(start, end,
                                        for_slider=for_slider,
                                        exact_end=exact_end)

    def delay(self) -> float:
        # Sample then sleep for inter-action delay.
        # 采样动作间隔并真实 sleep。
        v = self.timing.delay_between_actions()
        time.sleep(v)
        return v

    def think(self) -> float:
        # Sample then sleep for "thinking" pause.
        # 采样思考停顿并真实 sleep。
        v = self.timing.think()
        time.sleep(v)
        return v

    def after_open(self) -> float:
        # Sample then sleep for post-launch pause.
        # 采样启动后停留并真实 sleep。
        v = self.timing.after_open()
        time.sleep(v)
        return v

    def start_wait(self) -> float:
        # Random start-time jitter (no sleep).
        # 启动时刻随机偏移（不 sleep）。
        return self.timing.start_wait()

    def in_wake_window(self, now=None) -> bool:
        # Whether the current time is inside the wake window.
        # 当前时刻是否在作息窗口内。
        return self.timing.in_wake_window(now)

    def tap(self) -> float | None:
        # Record one tap; return cooldown seconds if triggered, else None.
        # 记录一次点击；触发冷却时返回秒数，否则 None。
        return self.timing.tap()

    def captcha_cooldown(self) -> float:
        # Session-level cooldown after captcha failure.
        # 验证码失败后的会话级冷却。
        return self.timing.captcha_cooldown()
