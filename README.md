# touch-humanization

拟人化触摸轨迹、时序与传感器模拟，供 Android 自动化项目复用。

- **零运行时依赖**：仅用 Python 标准库。
- **三段职责**：`kinematics`（贝塞尔轨迹 / Fitts 步数 / 微颤 / 过冲）、
  `timing`（对数正态时序 / 作息窗口 / 冷却）、`sensors`（传感器序列 + 死寂检测）。
- **单一随机源**：`Humanizer` 内部一个 `random.Random` 贯穿三个模块；每个模块也可单独使用，
  此时各自持有实例级 `Random`。同 seed 全链路可复现。
- **CI lint**：禁止 `random.seed`、全局 `random.*`、`numpy.random`。

## 安装

```bash
pip install -e .[dev]
```

## 快速使用

```python
from touch_humanization import Humanizer

h = Humanizer(seed=42)

# 1. 生成一段人类化滑动轨迹
g = h.gesture((100, 1800), (900, 400))
for (x, y), dt in zip(g.points, g.intervals):
    print(x, y, dt)

# 2. 采时序（不 sleep）
d = h.timing.delay_between_actions()

# 3. 采样传感器序列
rows = h.sensors.generate(mode="walking", fs=100.0, duration=2.0)
print(h.sensors.is_dead(rows))  # False
```

## Web UI（交互式：起终点 + seed + Generate + Canvas）

```bash
touch-humanization-web --port 8765
# 浏览器打开 http://127.0.0.1:8765/
```

## 测试与 lint

```bash
pytest -q
python tools/lint_random.py
```

## 许可证

MIT。上游算法参考：pyclick（MIT）、ghost-cursor（ISC）、bezier-mouse-js（MIT），详见 `LICENSE`。
