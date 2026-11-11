# 名称可用性（阶段 0）

## 结论

| 名称 | 类型 | 状态 | 依据 |
|---|---|---|---|
| `android-humanizer` | PyPI 包名 | **未占用** | 交接摘要记录（见下方"验证记录"） |
| `android-humanizer` | GitHub 仓库名 | **未占用** | 交接摘要记录（见下方"验证记录"） |
| `android_humanizer` | Python 模块名 | 本仓库使用 | 与包名一致，下划线替换连字符 |

## 验证记录

**来源**：交接摘要（V6.1 冻结时由双方确认）。

**记录原文**：
> 名称可用性：GitHub `android-humanizer` 与 PyPI `android-humanizer` 搜索均**未占用**。

**验证方式（发布前需复核）**：

```bash
# PyPI
curl -s -o /dev/null -w "%{http_code}\n" https://pypi.org/pypi/android-humanizer/json
# 404 = 可用；200 = 已占用

# GitHub（按包名全局搜索；注意 /repos/<name> 缺 owner 会恒 404，不能用于判断）
curl -s "https://api.github.com/search/repositories?q=android-humanizer+in:name" \
  | python -c "import sys,json;print(json.load(sys.stdin)['total_count'])"
# 0 = 无同名仓库；>0 = 逐条核对 owner
```

**复核时机**：
- 阶段 0 结束前（本文件落盘时已记录交接摘要结论）
- **首次 `twine upload` 前 24 小时内必须再查一次**（PyPI 名称可被他人抢注）

## 现状备注

GitHub 仓库 `MassChargeRatio/android-humanizer` 已由本项目创建并公开（CI/Pages/Release 均已配置）。PyPI 侧 `android-humanizer` 截至本文落盘仍未发布、未占用。

## 风险与备选

若首次发布前发现 `android-humanizer`（PyPI）已被占用，备选名（按优先级）：

1. `humanized-automation` — 覆盖手势/时序/传感器三层能力
2. `humanize-input` — 强调"拟人输入"
3. `android-humanizer` — 若确认只服务 Android

**注意**：改名后本文件需重做，且 `pyproject.toml`、`README.md`、`LICENSE` 的包名引用需同步更新。

## 已确认不做的名称

- 不使用 `android-humanizer` 的拼写变体（`touchhumanization`、`android_humanizer` 作为包名）——PyPI 生态惯例是连字符包名 + 下划线模块名。
- 不在包名里嵌入版本号（`android-humanizer-v6`）——语义化版本由 `pyproject.toml` 的 `version` 字段承载。
