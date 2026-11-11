# 上游溯源（阶段 0）

## 溯源目标

交接摘要要求补齐原仓 `human_trajectory.py` 中五个核心函数的完整源码，用于审计其算法来源与许可证合规性。

## 五个核心函数

以下函数位于原仓 `human_trajectory.py`，已在交接包 `ALL-IN-ONE-WITH-SOURCE.md` 的源码部分取得完整实现：

| 函数 | 类型 | 作用 | 原仓位置 |
|---|---|---|---|
| `_bezier3` | `@staticmethod`（`HumanTrajectory` 类内） | 三次贝塞尔曲线采样 | `human_trajectory.py` |
| `_control_points` | 实例方法（`HumanTrajectory` 类内） | 生成垂直方向随机偏移的控制点 | `human_trajectory.py` |
| `_smoothstep` | 模块级函数 | 慢-快-慢速度轮廓 | `human_trajectory.py` |
| `_ease_out_quad` | 模块级函数 | easeOutQuad 缓动 | `human_trajectory.py` |
| `_gauss` | 模块级函数 | 高斯采样（无 numpy 时 Box-Muller 近似） | `human_trajectory.py` |

## 上游对应关系

| 函数 | 上游参考 | 上游许可证 | 说明 |
|---|---|---|---|
| `_bezier3` | bezier-mouse-js（三次贝塞尔）+ pyclick（伯恩斯坦形式） | MIT + MIT | 本项目采用三次贝塞尔标准形式，与 bezier-mouse-js 一致 |
| `_control_points` | pyclick（法向偏移）+ ghost-cursor（单侧随机） | MIT + ISC | 控制点沿垂直主方向单侧偏移，幅度与距离成比例 |
| `_smoothstep` | pyclick（ease-in-out 速度轮廓） | MIT | 标准 smoothstep `3t² - 2t³` |
| `_ease_out_quad` | pyclick / bezier-mouse-js | MIT | 标准 easeOutQuad `1 - (1-t)²` |
| `_gauss` | ghost-cursor（高斯抖动） | ISC | Box-Muller 变换，零 numpy 依赖 |

## 本项目实现

`touch_humanization/kinematics/trajectory.py` 中：

- `_bezier3` / `_control_points` / `_smoothstep` / `_ease_out_quad` / `_gauss` **保留同名**，便于与原仓对照审计。
- `_control_points` 改为接收 `rng: random.Random` 参数（原仓使用全局 `random`），满足 V6.1 的"实例级随机源"约定。
- `_gauss` 改为接收 `rng` 参数，不再依赖 numpy。
- 其余三个函数为纯函数，签名与原仓一致。

## 与原仓的差异

| 差异 | 原仓 | 本项目 | 原因 |
|---|---|---|---|
| 随机源 | 全局 `random.*` | 实例 `rng` 参数 | V6.1 冻结约定 |
| numpy 依赖 | `_gauss` 依赖 numpy | Box-Muller 纯 Python | 零运行时依赖 |
| 类结构 | `HumanTrajectory` 类 | `Kinematics` 类 + 模块级纯函数 | 门面架构调整 |
| 滑块分支 | `for_slider=True` 参数 | `for_slider` 参数 + `_slider` 私有方法 | 行为等价，结构更清晰 |

## 审计结论

- 五个函数完整可审计，上游来源可追溯。
- 上游许可证（pyclick MIT / ghost-cursor ISC / bezier-mouse-js MIT）均与 MIT 兼容。
- 本项目实现为**算法移植**，非代码复制；原仓无许可证文件，不直接复制原仓代码。
- **阶段 0 上游溯源完成**，可进入阶段 1。

## 待办

- [ ] 首次发布前复核三个上游仓库的 `LICENSE` 文件（见 `license-audit.md` 待办）
- [ ] 若上游任一许可证变更，重新评估兼容性并更新本文件
