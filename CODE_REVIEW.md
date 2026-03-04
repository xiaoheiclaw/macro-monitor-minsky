# Code Review Report: Macro Monitor Minsky

**Reviewer**: code-reviewer  
**Date**: 2026-03-04  
**Commit**: HEAD (current working tree)  
**Overall Grade**: **B+**

---

## 1. Executive Summary

这是一个设计精良的三层宏观经济风险预警系统，基于 Minsky 金融不稳定假说构建。项目在**领域建模**和**方法论严谨性**方面表现出色——每个因子都经过 5-Gate 验证、IC/AUC 回测，并有完整的方法论文档。代码整体结构清晰，三层分离（Structure/Crack/Trend）逻辑合理。

**主要优点**：
- 领域设计深思熟虑，三层抽象准确反映了 Minsky 理论
- 因子验证框架（5-Gate）系统化，避免了数据挖掘
- 配置集中管理，权重和阈值均有理论依据
- 完善的 release lag 处理，防止 look-ahead bias

**主要问题**：
- `__pycache__` 被提交到 Git（无 `.gitignore`）
- `system_orchestrator.py` 过于庞大（1138 行），职责过多
- 测试严重不足（仅 1 个测试文件，且已过时，引用不存在的 API）
- `sys.path` 操控过度，模块间耦合通过路径 hack 实现
- v1/v2 规则引擎并行存在，v1 `_determine_system_state` 是 dead code 但未标记

| 维度 | 评分 | 说明 |
|------|------|------|
| 架构质量 | A- | 三层分离好，但 orchestrator 太胖 |
| 代码质量 | B | 命名好、文档好，但 DRY 不足，sys.path hack 多 |
| 数据流 | A | release lag 处理到位，无 look-ahead bias |
| 配置管理 | A | 集中配置，阈值有理论依据 |
| 错误处理 | B- | 大量 bare except/warnings.filterwarnings('ignore') |
| 测试覆盖 | D | 仅 1 个过时测试文件，无 pytest |
| 安全 | B+ | API key 从环境变量读取，但无 .gitignore |
| 性能 | B | 关键路径有优化空间（percentile 计算 O(n²)） |
| 部署就绪度 | B | Prefect flow 有但 Streamlit 未容器化 |
| 待清理 | C | `__pycache__` 提交、dead code、过时测试 |

---

## 2. 模块详细问题列表

### 2.1 `config.py` (343 行) — 统一配置

| # | Severity | 问题 | 行号 | 说明 |
|---|----------|------|------|------|
| 1 | Minor | `FRED_API_KEY` 在模块导入时立即求值 | L22-27 | 如果环境变量未设置，即使不使用 FRED API 也会触发 warning。应延迟到首次使用时检查 |
| 2 | Nitpick | `SYSTEM_THRESHOLDS['fuel_score']` 和 `FUEL_STATE_THRESHOLDS` 重复定义 | L117-130, L146-151 | 两组阈值映射 fuel score 到状态，数值不同（20/40/60/80 vs 40/60/80/100），容易混淆 |
| 3 | Minor | `CRACK_CONFIG['thresholds']` 中的值与 `CrackScore._get_state` 使用的值不一致 | L111-116 | 配置定义了 `STABLE: 0.5, EARLY_CRACK: 1.0`，但 `CrackScore` 的 `_get_state` 直接引用这些值作为上界而非下界，语义不直观 |
| 4 | Nitpick | 中英文混合注释 | 全文件 | Rule Engine 部分大量中文注释（`# 状态乘数`），与顶部英文注释风格不统一 |

### 2.2 `core/fuel_score.py` (302 行) — FuelScore

| # | Severity | 问题 | 行号 | 说明 |
|---|----------|------|------|------|
| 1 | Minor | `sys.path.insert(0, _parent_dir)` hack | L32-33 | 应通过 proper package 安装解决，而非运行时修改 sys.path |
| 2 | Minor | `compute_history` 遍历每行计算 score | L173-185 | 逐行 iterating DataFrame 效率低。可用 `apply` 或向量化 |
| 3 | Nitpick | `_get_signal` 返回 `'EXTREME LOW'` 但其他地方返回 `'EXTREME_LOW'`（带下划线） | L119 vs orchestrator | 风格不统一 |

### 2.3 `core/crack_score.py` (351 行) — CrackScore

| # | Severity | 问题 | 行号 | 说明 |
|---|----------|------|------|------|
| 1 | Major | `sys.path.insert(0, ...)` 不检查是否已存在 | L31 | 每次 import 都会重复插入，与 `fuel_score.py` 的做法不一致（后者有 `if _parent_dir not in sys.path`） |
| 2 | Minor | `directions` 字典硬编码在方法内部 | L105-112 | 应放入 `config.py` 或 `CRACK_CONFIG` |
| 3 | Minor | `_compute_crack_signal` 内的 `intensity_func` 使用 lambda + apply | L118-127 | 对大 Series 效率不佳，可向量化 |
| 4 | Minor | `_compute_total_score` 中 `for idx in all_indices` 逐行遍历 | L160-181 | 对于长时间序列这会很慢。可用矩阵运算 |
| 5 | Nitpick | `zscore_window` 构造参数默认 96 但 `CRACK_CONFIG` 中是 120 | L50 vs config L109 | 默认值不一致，虽然 config 值会覆盖 |

### 2.4 `core/trend_score.py` (217 行) — TrendScore wrapper

| # | Severity | 问题 | 行号 | 说明 |
|---|----------|------|------|------|
| 1 | Major | `sys.path.insert(0, trend_package_dir)` 在运行时 | L77-81 | 可能与其他 import 冲突。`trend_score` 既是 package 也是 module，命名歧义 |
| 2 | Minor | `compute_history` 中 `except Exception as e: return pd.DataFrame()` | L139-140 | 吞掉所有异常，调试困难 |
| 3 | Minor | `clear_cache` 直接访问内部 `_data_cache` | L155 | 违反封装，如果内部实现改变会 break |

### 2.5 `data/loader.py` (732 行) — 数据加载器

| # | Severity | 问题 | 行号 | 说明 |
|---|----------|------|------|------|
| 1 | Major | `load_trend_factors` 中的 `TREND_DATA_FILES` 字典与实际文件名不匹配 | L183-195 | 列出了 `a_vix.csv`, `a_vix_term.csv` 等，但实际文件是 `a1_vts.csv`, `a2_skew.csv`。这个方法可能从未成功运行过 |
| 2 | Minor | `_download_cape_from_multpl` 中 Web scraping 无重试机制 | L336-373 | 如果 multpl.com 暂时不可用，直接失败 |
| 3 | Minor | `_download_spx_from_yahoo` 使用 `yfinance` 但未在 try 外 import | L413-431 | 放在方法内 import，但如果 yfinance 不可用会给出不清晰的错误 |
| 4 | Minor | `print` 用于日志输出 | 全文件 | 生产代码应使用 `logging` 模块 |
| 5 | Nitpick | `load_structure_factors` 中的 `print("=" * 60)` | L79-81 | 加载数据时打印大量分隔线，在 Streamlit 环境中会造成噪音 |
| 6 | Major | `generate_lagged_data` 中硬编码了文件列表 | L300-312 | 与 `FACTOR_FILES` 配置重复，如果新增因子需要改两处 |

### 2.6 `utils/transforms.py` (283 行) — 变换函数

| # | Severity | 问题 | 行号 | 说明 |
|---|----------|------|------|------|
| 1 | Major | `compute_rolling_percentile` 使用 Python for-loop 逐点计算 | L44-64 | O(n × window) 复杂度，对长序列非常慢。可用 `pd.Series.rolling().apply()` 或 `bottleneck`/`numba` 加速 |
| 2 | Minor | `compute_credit_gap` 也使用 Python for-loop | L133-161 | 同上，重复了 `compute_rolling_percentile` 的低效实现 |
| 3 | Minor | `compute_rolling_percentile` 和 `compute_credit_gap` 中的 percentile 计算逻辑重复 | L56-62, L153-157 | 违反 DRY，应提取公共函数 |

### 2.7 `system_orchestrator.py` (1138 行) — 系统协调器

| # | Severity | 问题 | 行号 | 说明 |
|---|----------|------|------|------|
| 1 | **Critical** | 文件过大，职责过多 | 全文件 | 包含：数据更新、Structure/Crack/Trend 计算、v1 和 v2 规则引擎、Dashboard CLI 输出、JSON 导出、历史数据计算、推荐生成、升级触发器计算。应拆分为至少 3-4 个模块 |
| 2 | Major | `_determine_system_state`（v1 规则）与 `_apply_rules`（v2）并存 | L277-310, L335-342 | v1 的 `_determine_system_state` 似乎是 dead code（`compute_portfolio_action` 使用它，但主流程用 v2），但没有标记 deprecated |
| 3 | Major | `compute_structure_output` 中硬编码权重 | L207-213 | `weights = {'V1': 0.122, 'V4': 0.046, ...}` 与 `config.py` 中的 `FUEL_WEIGHTS_IC` 重复且不完全一致（缺少 V2） |
| 4 | Major | `update_structure_data` 调用不存在的脚本 | L115-133 | 调用 `structure/data_loader.py`，但该文件不存在（实际是 `data/loader.py`）。此方法永远返回 error |
| 5 | Minor | `warnings.filterwarnings('ignore')` 全局抑制 | L18 | 可能隐藏重要警告 |
| 6 | Minor | `FACTOR_NAMES` 和 `MODULE_NAMES` 重复定义 | L42-55 | 与 `config.py` 中的 `FACTOR_NAMES` 重复 |
| 7 | Minor | `print_dashboard_v2` 中大量硬编码的格式化字符串 | L450-555 | 70+ 行的 CLI 格式化逻辑，应该提取到独立的 formatter 模块 |
| 8 | Minor | `compute_crack_output` 中的字段映射逻辑 | L245-275 | `signal` vs `delta_z` 的映射注释表明接口不稳定 |
| 9 | Nitpick | 混合使用 f-string 和 format string | 全文件 | 风格不统一 |

### 2.8 `orchestrator/rules.py` (124 行) — 规则引擎

| # | Severity | 问题 | 行号 | 说明 |
|---|----------|------|------|------|
| 1 | Minor | `_build_rationale` 中 `R8f` 模板缺失 | L67-79 | Fallback default 使用 `R8f` 但模板字典中最后一个是 `R8e`，会 fall through 到默认值 |
| 2 | Nitpick | 规则条件使用 list（`['CRITICAL']`），查找时 `in` 操作为 O(n) | L45-50 | 量级小影响可忽略，但语义上 set 更合适 |

### 2.9 `orchestrator/risk_budget.py` (73 行) — 风险预算计算器

| # | Severity | 问题 | 行号 | 说明 |
|---|----------|------|------|------|
| 1 | Nitpick | 缺少输入验证 | L28-55 | `fuel_score` 无范围检查，`system_state` 等无合法值检查 |
| 2 | Nitpick | `round(base, 3)` 精度处理不一致 | L52-53 | `base` 和 `final` round 到 3 位，其他字段不 round |

### 2.10 `trend/trend_score/trend_score.py` (1059 行) — TrendScore

| # | Severity | 问题 | 行号 | 说明 |
|---|----------|------|------|------|
| 1 | Major | 文件过大，混合了计算逻辑和 IO | 全文件 | 数据加载、因子计算、模块聚合、趋势聚合、校准、历史计算全在一个类中 |
| 2 | Minor | `compute_history` 中逐日计算 | L821-876 | `compute_for_date` 在循环中反复调用，每次都重新解析所有因子。可预先向量化 |
| 3 | Minor | `get_factor_value` 中的列名猜测逻辑 | L471-480 | `possible_cols` 匹配逻辑脆弱，移除下划线后匹配可能产生错误匹配 |
| 4 | Nitpick | v3.0, v4.0, v4.1, v4.2 版本标记散布在 docstring 中 | 多处 | 建议统一到 CHANGELOG |

### 2.11 `trend/data/cache_all_factors.py` (991 行) — 数据缓存

| # | Severity | 问题 | 行号 | 说明 |
|---|----------|------|------|------|
| 1 | Major | 大量重复的缓存函数模式 | 全文件 | `cache_a1_vts()`, `cache_a2_skew()`, `cache_a3_move()` 等结构几乎相同，应提取模板函数 |
| 2 | Minor | `fetch_ishares_shares_outstanding` Web scraping 无速率限制 | L580-620 | 连续请求 3 个 ETF 页面可能被限流 |
| 3 | Minor | `compute_percentile` 和 `compute_zscore` 与 `utils/transforms.py` 中的同名函数重复 | L39-51 | 两个模块各自实现了 rolling percentile 和 z-score，实现方式还不同 |
| 4 | Nitpick | HTML 解析使用 `html.parser` 而不是更健壮的 `lxml` | L614 | `html.parser` 对格式不规范的 HTML 容错性差 |

### 2.12 `lib/factor_validation_gates.py` (759 行) — 验证门

| # | Severity | 问题 | 行号 | 说明 |
|---|----------|------|------|------|
| 1 | Minor | 函数签名中 `step: int = 10` 但搜索空间是百分位 0-100 | L27 | 步长 10 意味着只搜索 10 个可能的 lower 值，可能遗漏最优区间 |
| 2 | Nitpick | `STANDARD_WALKFORWARD_WINDOWS` 硬编码训练窗口起始于 1960 | L699-704 | 如果数据从 1980 开始，前两个窗口的训练集可能不完整 |
| 3 | Nitpick | 无 type hints 导入 (`from typing import ...`) 但使用了 `Dict`, `List` 等旧式标注 | 全文件 | Python 3.9+ 可直接用 `dict`, `list` |

### 2.13 `lib/regime_analysis.py` (652 行) — 分区分析

| # | Severity | 问题 | 行号 | 说明 |
|---|----------|------|------|------|
| 1 | Minor | `compute_forward_max_drawdown` 逐日 Python 循环 | L51-60 | O(n × horizon)，对长序列很慢。可用 sliding window 优化 |
| 2 | Minor | `_newey_west_se` 重复实现 | L280-300 | 与 `lib/hac_inference.py` 中的 `newey_west_se` 功能重复 |
| 3 | Nitpick | `from scipy.stats import spearmanr` 在文件顶部导入但在 `run_quintile_analysis` 中又重复导入 | L5, L527 | 冗余 import |

### 2.14 `dashboard_app.py` (1361 行) — Streamlit 仪表盘

| # | Severity | 问题 | 行号 | 说明 |
|---|----------|------|------|------|
| 1 | Major | 文件过大 | 全文件 | 包含：页面配置、CSS、helper 函数、图表生成（7个 chart 函数）、数据加载、主页面逻辑。应拆分 |
| 2 | Major | `load_history_data` 内 `import yfinance as yf` + `yf.download()` | L635-642 | 每次加载历史数据都从 Yahoo Finance 实时下载 SPX。即使有 5min cache，首次加载会很慢。应优先使用本地 CSV |
| 3 | Minor | 7 个大型图表函数（`make_*_chart`）占 600+ 行 | L150-600 | 重复的 Plotly 配置代码，应提取公共图表 builder |
| 4 | Minor | `get_fuel_comparison` 每次实例化新的 `FuelScore` | L621-624 | 但实际上 FuelScore 内部会重新加载数据，与主 orchestrator 的数据不共享 |
| 5 | Nitpick | 硬编码的 CSS 字符串 | L62-69 | 应放到独立 CSS 文件 |
| 6 | Nitpick | 危机期间列表重复出现 3 次 | L389, L581, L670 | 应定义为常量 |

### 2.15 `prefect_flow.py` / `deploy.py` — 部署

| # | Severity | 问题 | 行号 | 说明 |
|---|----------|------|------|------|
| 1 | Minor | `prefect_flow.py` 不使用 `@task` 装饰器 | 全文件 | 所有工作都在 `@flow` 内直接执行，失去了 Prefect 的任务级重试和监控能力 |
| 2 | Minor | `deploy.py` 硬编码 Docker workspace 路径 | L10 | `/workspace/indicator_test` 仅在特定 Docker 环境有效 |
| 3 | Nitpick | `prefect_flow.py` 中没有错误处理 | 全文件 | 任何一步失败会导致整个 flow 中止 |

### 2.16 `trend/trend_score/test_trend_score.py` — 测试

| # | Severity | 问题 | 行号 | 说明 |
|---|----------|------|------|------|
| 1 | **Critical** | 测试引用不存在的 API | L13-16, L82 | `from trend.trend_score.config import FACTOR_WEIGHTS, get_normalized_weights` — 这些在当前 `config.py` 中不存在（已被 v2.0 重构移除）。测试无法运行 |
| 2 | Major | 测试不使用 pytest 框架 | 全文件 | 使用手动 print + assert，无法被 CI 发现 |
| 3 | Major | 测试依赖实际数据文件 | L120-140 | 没有 mock/fixture，需要真实 CSV 才能运行 |

---

## 3. 好的实践（值得保留）

### 3.1 领域建模

- **三层分离设计出色**：Structure（季度结构性）→ Crack（月度变化率）→ Trend（日度市场压力）层次清晰，频率递减
- **Minsky 理论映射准确**：FuelScore = 燃料积累，CrackScore = 裂纹扩展，TrendScore = 市场点火
- **状态机设计**：NORMAL → CAUTIOUS → DEFENSIVE → CRISIS 四级递进，配合 HOLD/DE-RISK/HEDGE/EXIT 行动

### 3.2 数据工程

- **Release Lag 处理**：`RELEASE_LAG` 配置 + `apply_release_lag()` 正确模拟了"决策时可用数据"，这是避免 look-ahead bias 的关键
- **Lagged vs Raw 分离**：`structure/data/raw/` 和 `structure/data/lagged/` 两套数据，生产用 lagged，研究用 raw
- **增量更新**：`update_cape_data()`、`update_spx_data()` 支持增量追加，不需要全量重下载

### 3.3 验证框架

- **5-Gate 验证系统**（`factor_validation_gates.py`）：系统化地检验因子的实时性、OOS Lift、Leave-One-Crisis-Out 稳健性、Lead Time、Zone 稳定性
- **数据驱动权重**（TrendScore v4.0）：基于 AUC/IC/Lead 计算 reliability 权重，而非拍脑袋
- **FACTOR_VALIDATION_METRICS**：每个因子的验证指标都有据可查

### 3.4 规则引擎

- **声明式规则**（`config.py` PRIORITY_RULES）：规则以数据结构描述而非 if-else 硬编码，易于审计和修改
- **Fallback 规则**：当 Trend 数据质量不足时有独立的降级规则链
- **审计友好输出**：`triggered_rule` 字段记录了触发的具体规则，可追溯

### 3.5 代码质量

- **文档字符串充分**：几乎所有类和函数都有 docstring，包含参数说明和使用示例
- **配置集中**：`config.py` 集中管理所有阈值、权重、规则，避免 magic numbers 散落
- **因子经济含义注释**（`dashboard_app.py` 中的 `FUEL_FACTOR_EXPLANATIONS`）：帮助理解每个指标的业务意义

---

## 4. 重构建议（优先级排序）

### P0 — 必须立即修复

1. **添加 `.gitignore`**
   - 添加 `__pycache__/`, `*.pyc`, `.env`, `*.egg-info/` 等
   - 清除已提交的 `__pycache__` 文件：`git rm -r --cached **/__pycache__`

2. **修复 `update_structure_data` 中的 broken path**
   - `structure/data_loader.py` 不存在，改为使用 `data.loader.DataLoader` 直接调用

3. **修复过时测试**
   - `test_trend_score.py` 引用不存在的 `FACTOR_WEIGHTS`/`get_normalized_weights`
   - 要么更新测试适配 v2.0 API，要么删除并重写

### P1 — 高优先级

4. **拆分 `system_orchestrator.py`**
   ```
   orchestrator/
   ├── __init__.py
   ├── rules.py          (已有)
   ├── risk_budget.py     (已有)
   ├── state_machine.py   ← 从 orchestrator 提取状态判定逻辑
   ├── data_updater.py    ← 从 orchestrator 提取数据更新逻辑
   ├── cli_dashboard.py   ← 从 orchestrator 提取 CLI 格式化
   └── explanation.py     ← 从 orchestrator 提取解释/推荐/trigger 逻辑
   ```

5. **消除 `sys.path` hack**
   - 通过 `pip install -e .` 安装项目为可编辑包
   - 在 `pyproject.toml` 中已有 package 配置，但运行时仍使用 path hack
   - 清除所有 `sys.path.insert(0, ...)` 调用

6. **统一 rolling percentile 实现**
   - `utils/transforms.py`、`trend/data/cache_all_factors.py`、`trend/trend_score/intensity.py` 三处各自实现
   - 提取到 `utils/transforms.py` 一处，其他引用它

7. **清理 v1 dead code**
   - `_determine_system_state()` 标记为 deprecated 或删除
   - `compute_portfolio_action()` 标记为 deprecated（如果 v2 是主流程）
   - `print_dashboard()`（v1 版本）同理

### P2 — 中优先级

8. **拆分 `dashboard_app.py`**
   ```
   dashboard/
   ├── app.py             ← 主页面逻辑
   ├── charts.py          ← 7个图表函数
   ├── components.py      ← gauge, bar chart 等组件
   ├── constants.py       ← 颜色、解释文本
   └── data_loader.py     ← 缓存数据加载
   ```

9. **引入 `logging` 替代 `print`**
   - `data/loader.py`、`cache_all_factors.py` 中的大量 print 改为 logging
   - Streamlit 环境中 print 输出会造成干扰

10. **性能优化：向量化 percentile 计算**
    ```python
    # 当前: O(n × window) Python loop
    for i in range(len(series)):
        historical = series.iloc[start:i+1]
        pctl = (historical < current).sum() / len(historical)

    # 改进: 使用 pandas rolling + rank
    result = series.rolling(window).apply(lambda x: (x[:-1] < x[-1]).sum() / (len(x)-1))
    ```

11. **加入 Prefect task 装饰器**
    - 将 `cache_a1_vts()` 等函数包装为 `@task`
    - 获得任务级别的重试、超时、监控能力

12. **统一阈值系统**
    - `SYSTEM_THRESHOLDS['fuel_score']` vs `FUEL_STATE_THRESHOLDS` 合并
    - `CRACK_CONFIG['thresholds']` 值的语义（上界 vs 下界）明确标注

### P3 — 低优先级

13. **危机期间常量提取**
    - `dashboard_app.py` 中重复 3 次的 `crises = [...]`
    - 提取到 `config.py` 或 `constants.py`

14. **拆分 `trend/trend_score/trend_score.py`**
    - 数据加载 → `data_loader.py`
    - 因子/模块计算 → `calculator.py`
    - 校准 → `calibrator.py`

15. **`cache_all_factors.py` 模板化**
    ```python
    def cache_factor(name, loader_func, transforms, output_file):
        """通用缓存模板"""
        data = loader_func()
        df = pd.DataFrame({f'{name}_raw': data})
        for transform_name, transform_func in transforms:
            df[transform_name] = transform_func(data)
        df.to_csv(output_file)
    ```

16. **Python 3.9+ 类型标注**
    - `Dict[str, float]` → `dict[str, float]`
    - `List[str]` → `list[str]`
    - `Optional[str]` → `str | None`

---

## 5. 行动项清单

### 🔴 Critical（立即）

- [ ] 创建 `.gitignore` 并清除已提交的 `__pycache__`
- [ ] 修复 `test_trend_score.py` 或删除（当前无法运行）
- [ ] 修复 `update_structure_data` 的 broken path

### 🟡 Major（1-2 周内）

- [ ] 拆分 `system_orchestrator.py`（>1100 行 → 多个 <300 行模块）
- [ ] 消除所有 `sys.path.insert` hack，改用 `pip install -e .`
- [ ] 统一 rolling percentile/zscore 实现（消除 3 处重复）
- [ ] 标记/删除 v1 dead code（`_determine_system_state`, `compute_portfolio_action`, `print_dashboard`）
- [ ] 修复 `load_trend_factors` 中的错误文件名映射
- [ ] 添加基础单元测试（至少覆盖 FuelScore, CrackScore, RuleEngine, RiskBudget）

### 🟢 Minor（逐步改进）

- [ ] 拆分 `dashboard_app.py` 为多模块
- [ ] `print` → `logging` 迁移
- [ ] 向量化 percentile 计算（性能优化）
- [ ] Prefect flow 添加 `@task` 装饰器
- [ ] 统一阈值配置命名
- [ ] 提取危机期间常量
- [ ] 中英文注释风格统一

### 📝 Nitpick（可选）

- [ ] Python 3.9+ 类型标注现代化
- [ ] `orchestrator/rules.py` 中条件列表改为 set
- [ ] `risk_budget.py` 添加输入验证
- [ ] 拆分 `trend_score.py`（1059 行）

---

## 附录：文件大小排名与复杂度评估

| 文件 | 行数 | 复杂度评估 | 建议 |
|------|------|-----------|------|
| `dashboard_app.py` | 1361 | 高（UI+数据+图表） | 拆分为 4 个文件 |
| `system_orchestrator.py` | 1138 | 高（全能类） | 拆分为 4-5 个文件 |
| `trend/trend_score/trend_score.py` | 1059 | 中高（单类） | 拆分为 3 个文件 |
| `trend/data/cache_all_factors.py` | 991 | 中（重复模式） | 模板化可降至 ~400 行 |
| `lib/factor_validation_gates.py` | 759 | 中（独立工具） | 可保持 |
| `data/loader.py` | 732 | 中（IO 密集） | 可保持，修复映射 |
| `lib/regime_analysis.py` | 652 | 中（独立工具） | 可保持 |
| `config.py` | 343 | 低（纯配置） | 合并重复定义 |
| `core/crack_score.py` | 351 | 低 | 可保持 |
| `core/fuel_score.py` | 302 | 低 | 可保持 |
