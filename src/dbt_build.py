"""独立进程运行dbt，避免构建连接与页面只读连接混用。"""
import sys
from dbt.cli.main import dbtRunner

if __name__ == '__main__':
    result = dbtRunner().invoke(sys.argv[1:])
    if not result.success:
        if result.exception:
            print(result.exception, file=sys.stderr)
        raise SystemExit(1)
