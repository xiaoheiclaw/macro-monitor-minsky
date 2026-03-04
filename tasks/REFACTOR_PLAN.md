# Macro Monitor Minsky - 重构计划

基于 CODE_REVIEW.md 的发现，分三条并行线执行。

## Wave 1（并行，三条线）

### Line A: Foundation & Data Layer
**负责文件**: .gitignore, data/loader.py, trend/trend_score/test_trend_score.py
- [x] 创建 .gitignore
- [x] git rm -r --cached 清理所有 __pycache__
- [x] 修复 data/loader.py 中 load_trend_factors 的错误文件名映射
- [x] 修复/重写 test_trend_score.py（当前引用不存在的 API）

### Line B: Core & Utils Cleanup
**负责文件**: core/fuel_score.py, core/crack_score.py, core/trend_score.py, utils/transforms.py, trend/data/cache_all_factors.py
- [x] 移除 core/*.py 中所有 sys.path.insert hack
- [x] 统一 rolling percentile/zscore 实现到 utils/transforms.py
- [x] trend/data/cache_all_factors.py 中引用统一后的 transforms
- [x] print → logging 迁移（data 相关文件）

### Line C: Orchestrator Refactoring
**负责文件**: system_orchestrator.py → orchestrator/ 模块拆分
- [x] 拆出 orchestrator/state_machine.py（状态判定）
- [x] 拆出 orchestrator/data_updater.py（数据更新）
- [x] 拆出 orchestrator/cli_dashboard.py（CLI 格式化）
- [x] 拆出 orchestrator/explanation.py（解释/推荐/trigger）
- [x] 清理 v1 dead code（_determine_system_state, print_dashboard 等）
- [x] 修复 update_structure_data 的 broken path
- [x] system_orchestrator.py 保留为 thin wrapper，维持外部 import 兼容

## Wave 2（Wave 1 完成后）

### code-reviewer 验证
- [ ] 跑 python -m py_compile 验证所有文件语法
- [ ] 验证 pip install -e . 可用
- [ ] 验证 import 链路无 broken reference
- [ ] git commit

## 不在本次范围

- dashboard_app.py 拆分（P2）
- Prefect @task 装饰器（P2）
- 完整单元测试（P2，等重构稳定后）
- Python 3.9+ 类型标注（P3）
