#!/usr/bin/env bash
# macOS / Linux 一键启动：创建虚拟环境、装依赖、打开设计器
set -e
cd "$(dirname "$0")"

echo
echo "  宣讲会签到码工坊"
echo "  ------------------------------------------"
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "  [x] 没找到 python3，请先安装 Python 3.9+"
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  echo "  [1/3] 首次运行，创建虚拟环境..."
  python3 -m venv .venv
  echo "  [2/3] 安装依赖（第一次约 1-2 分钟）..."
  .venv/bin/python -m pip install -q --upgrade pip
  .venv/bin/python -m pip install -q -r requirements.txt
else
  echo "  [1/3] 虚拟环境已就绪"
fi

echo "  [2/3] 启动设计器..."
echo "  [3/3] 浏览器会自动打开 http://127.0.0.1:8848"
echo
echo "  Ctrl+C 停止服务。"
echo

exec .venv/bin/python -m xuanjqd preview
