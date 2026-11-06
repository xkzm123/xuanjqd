#!/usr/bin/env bash
# macOS / Linux 一键启动：检查依赖、启动界面
set -e
cd "$(dirname "$0")"

echo
echo "  宣讲会签到码"
echo "  ------------------------------------------"
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "  [x] 没找到 python3，请先安装 Python 3.9+"
  exit 1
fi

if ! python3 -c "import fastapi, uvicorn, segno, PIL, rich, typer" >/dev/null 2>&1; then
  echo "  [1/2] 缺少依赖，正在安装（只需要一次）..."
  python3 -m pip install -r requirements.txt
else
  echo "  [1/2] 依赖已就绪"
fi

echo "  [2/2] 启动界面，浏览器会自动打开..."
echo
echo "  Ctrl+C 停止服务。"
echo

exec python3 -m xuanjqd preview
