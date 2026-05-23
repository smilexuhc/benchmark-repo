#!/bin/bash
# 一键启动角色资产库（本地工具）。Ctrl+C 同时停止前后端。
cd "$(dirname "$0")"

if [ ! -d backend/.venv ]; then
  echo "首次运行：创建后端虚拟环境并安装依赖…"
  python3 -m venv backend/.venv
fi
backend/.venv/bin/pip install -q -r backend/requirements.txt
if [ ! -d frontend/node_modules ]; then
  echo "首次运行：安装前端依赖…"
  (cd frontend && npm install)
fi

echo "后端  http://localhost:8000"
echo "前端  http://localhost:5180"
trap 'kill 0' EXIT
(cd backend && .venv/bin/python main.py) &
(cd frontend && npm run dev) &
wait
