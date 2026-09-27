#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# 优先使用项目自带虚拟环境；venv 不可用（如系统缺 python3-venv）时退回已装好依赖的系统 python3。
if [ -x .venv/bin/python ] && .venv/bin/python -c "import fastapi, uvicorn" >/dev/null 2>&1; then
  exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
fi

if python3 -c "import fastapi, uvicorn" >/dev/null 2>&1; then
  exec python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
fi

# 系统 Python 缺依赖时再尝试建虚拟环境；建不出来就明确提示，而不是静默失败。
python3 -m venv .venv || { echo "无法创建虚拟环境，请安装 python3-venv，或先执行 pip install -r requirements.txt" >&2; exit 1; }
.venv/bin/pip install -q -r requirements.txt
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
