# touch-humanization

[![CI](https://github.com/MassChargeRatio/touch-humanization/actions/workflows/ci.yml/badge.svg)](https://github.com/MassChargeRatio/touch-humanization/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)

**在线演示（交互式轨迹预览）**：<https://masschargeratio.github.io/touch-humanization/>

拟人化触摸轨迹、时序与传感器模拟，供 Android 自动化项目复用。

- **零运行时依赖**：仅用 Python 标准库。 / Zero runtime dependencies: stdlib only.
- **三段职责**：`kinematics`（贝塞尔轨迹 / Fitts 步数 / 微颤 / 过冲）、
  `timing`（对数正态时序 / 作息窗口 / 冷却）、`sensors`（传感器序列 + 死寂检测）。
- **单一随机源**：`Humanizer` 内部一个 `random.Random` 贯穿三个模块；每个模块也可单独使用，
  此时各自持有实例级 `Random`。同 seed 全链路可复现。
  / Single random stream: one `random.Random` inside `Humanizer` shared by all three
  sub-modules; each module also works standalone with its own instance rng.
- **CI lint**：禁止 `random.seed`、全局 `random.*`、`numpy.random`。
- **注释中英双语**：代码注释、docstring、行内说明全部采用中英双语；UI 文案与日志消息保持原样。
  / Bilingual comments: docstrings and inline comments are English + Chinese;
  runtime strings (UI text, log messages) stay as-is.

## 安装 / Install

```bash
pip install -e .[dev]
```

## 快速使用 / Quick start

```python
from touch_humanization import Humanizer

h = Humanizer(seed=42)

# 1. 生成一段人类化滑动轨迹 / Generate a human-like swipe trajectory
g = h.gesture((100, 1800), (900, 400))
for (x, y), dt in zip(g.points, g.intervals):
    print(x, y, dt)

# 2. 采时序（不 sleep）/ Sample timing without sleeping
d = h.timing.delay_between_actions()

# 3. 采样传感器序列 / Sample a sensor sequence
rows = h.sensors.generate(mode="walking", fs=100.0, duration=2.0)
print(h.sensors.is_dead(rows))  # False
```

## Web GUI（交互式：手势轨迹 / 时序 / 传感器）

### 方式一：在线演示（无需安装）

浏览器直接打开：

**https://masschargeratio.github.io/touch-humanization/**

这是 GitHub Pages 托管的静态演示页（`site/` 目录），轨迹 tab 覆盖：

| 能力 | 说明 | 对应后端 |
|---|---|---|
| 起终点 / seed / 滑块模式 / 高级参数 | 与 Python `Kinematics` 参数对齐 | `kinematics` |
| Canvas 绘制 + 步间隔统计 | p50 / p95 实时展示 | `kinematics` |

在线演示是**纯前端静态页**（JS 移植同一套算法），不依赖 Python 后端；所有计算在浏览器内完成。时序与传感器 tab 请用本地服务（方式二）。

### 方式二：本地启动（完整功能，含三 tab、CSV 导出与 POST API）

```bash
# 1. 安装（含测试依赖）/ Install (with test deps)
pip install -e .[dev]

# 2. 启动本地 Web 服务 / Start the local web server
touch-humanization-web --port 8765
# 或 / or: python -m touch_humanization.web.server --port 8765

# 3. 浏览器打开 / Open in a browser
#    http://127.0.0.1:8765/
```

**启动参数 / CLI options**：

| 参数 | 默认 | 说明 |
|---|---|---|
| `--host` | `127.0.0.1` | 监听地址；改成 `0.0.0.0` 会暴露到局域网，不建议 |
| `--port` | `8765` | 监听端口 |
| `--no-browser` | 关闭 | 加此参数不自动打开浏览器 |

**三个 tab**：

| Tab | 能力 |
|---|---|
| 手势轨迹 | 起终点、seed、滑块模式、高级参数、Canvas 绘制、**逐点动画播放** |
| 时序 | 延迟分布直方图、作息窗口 24h 时间轴、冷却事件模拟 |
| 传感器 | 四种模式生成、三轴波形图、死寂判定明细、CSV 导出 |

**在线演示与本地服务的区别**：

| 能力 | 在线演示 | 本地服务 |
|---|---|---|
| 手势轨迹交互预览 | ✅ | ✅ |
| 时序 / 传感器 tab | ❌ | ✅ |
| 传感器 CSV 导出（`/api/sensors/csv`） | ❌ | ✅ 真实后端生成 |
| 通过 HTTP API 从其他程序调用 | ❌ | ✅ |

### 方式三：本地预览与线上一致的静态页

仓库根目录的 `site/` 是 Pages 的部署源。如需在本地查看与线上完全一致的静态页：

```bash
# 任选一个静态文件服务器 / any static file server
python -m http.server 8000 --directory site
# 浏览器打开 http://127.0.0.1:8000/
```

注意：`site/` 是纯静态页，不包含 Python 后端，因此没有 CSV 导出和 POST API。

**`site/` 与 `touch_humanization/web/static/` 的分工**（两者是不同的前端，不是同步副本）：

| 目录 | 定位 | 依赖 |
|---|---|---|
| `site/` | GitHub Pages 在线演示：纯前端移植同一套算法，开箱即用 | 零依赖，不调用任何 API |
| `touch_humanization/web/static/` | 本地 Web GUI（`touch-humanization-web`）的三 tab 控制台前端 | 必须配合 Python 后端的 `/api/*` 端点 |

修改算法展示逻辑时两处可能都需要调整；`web/static/` 的改动随包分发（wheel 内含），`site/` 的改动由 Pages 工作流自动部署。

### Web GUI 的 API（本地服务）

如果希望用脚本调用 Web GUI 背后的能力：

| 方法 | 路径 | 作用 |
|---|---|---|
| GET | `/api/health` | 健康检查 |
| POST | `/api/gesture` | 生成手势轨迹 |
| POST | `/api/timing/sample` | 采样延迟分布 |
| POST | `/api/timing/window` | 计算作息窗口区间 |
| POST | `/api/timing/cooldown` | 模拟冷却事件 |
| POST | `/api/sensors/generate` | 生成传感器序列 + 死寂判定 |
| POST | `/api/sensors/csv` | 导出 CSV（`text/csv`） |

请求体示例（`/api/gesture`）：

```json
{
  "start": [100, 1800],
  "end": [900, 400],
  "seed": 42,
  "for_slider": false
}
```

## 测试与 lint / Tests & lint

```bash
pytest -q
python tools/lint_random.py
```

## 许可证 / License

MIT。上游算法参考：pyclick（MIT）、ghost-cursor（ISC）、bezier-mouse-js（MIT），详见 `LICENSE`。
/ Upstream algorithm references: pyclick (MIT), ghost-cursor (ISC), bezier-mouse-js (MIT). See `LICENSE`.
