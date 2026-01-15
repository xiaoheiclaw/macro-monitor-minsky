#!/usr/bin/env python3
"""部署 Indicator flows 到 Prefect"""

import subprocess
from pathlib import Path

# 在 Docker 中使用 /workspace/indicator_test，本地使用实际路径
ROOT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = "/workspace/indicator_test"


def deploy_flow(func: str, name: str, cron: str = None):
    """部署单个 flow"""
    cron_arg = f", cron='{cron}'" if cron else ""

    # 直接用 serve 方式注册，不导入模块
    code = f"""
import sys
sys.path.insert(0, '{WORKSPACE_DIR}')

from prefect_flow import {func}

{func}.from_source(
    source='{WORKSPACE_DIR}',
    entrypoint='prefect_flow.py:{func}'
).deploy(
    name='{name}',
    work_pool_name='process',
    build=False,
    ignore_warnings=True{cron_arg}
)
"""
    result = subprocess.run(
        ["python", "-c", code],
        cwd=WORKSPACE_DIR if Path(WORKSPACE_DIR).exists() else ROOT_DIR,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(f"✓ {name}")
    else:
        print(f"✗ {name}: {result.stderr[:200]}")

    return result.returncode == 0


def main():
    print("=" * 50)
    print("部署 Indicator Flows")
    print("=" * 50)

    flows = [
        {
            "func": "indicator_data_update",
            "name": "Indicator 数据更新",
            "cron": "0 16 * * 1-5",  # UTC 16:00 = 北京 00:00, 工作日
        },
        {
            "func": "indicator_weekly_refresh",
            "name": "Indicator 周末刷新",
            "cron": "0 16 * * 0",  # UTC 16:00 = 北京 00:00, 周日
        },
    ]

    success = 0
    for f in flows:
        if deploy_flow(**f):
            success += 1

    print("=" * 50)
    print(f"完成: {success}/{len(flows)}")


if __name__ == "__main__":
    main()
