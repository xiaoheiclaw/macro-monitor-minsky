# /validate - 运行指标验证

验证指定的指标测试脚本并生成报告。

## 使用方法

```
/validate v6
/validate test_v2_interest_coverage.py
```

## 执行步骤

1. 查找匹配的 test_v*.py 文件
2. 设置 FRED_API_KEY 环境变量
3. 运行测试脚本
4. 检查输出目录是否生成
5. 打开 SUMMARY.md 查看结果

## 示例执行

```bash
FRED_API_KEY='your_key' python test_v6_shiller_pe.py
```

## 预期输出

- `V#_Name/01_all_methods.png` - 可视化图表
- `V#_Name/all_methods_data.csv` - 原始数据
- `V#_Name/SUMMARY.md` - 验证结论
