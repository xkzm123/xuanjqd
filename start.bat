@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 宣讲会签到码工坊

echo.
echo   宣讲会签到码工坊
echo   --------------------------------------------------
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo   [x] 没找到 python
  echo       请先安装 Python 3.9 或更高版本，安装时勾选 "Add python.exe to PATH"
  echo       https://www.python.org/downloads/
  echo.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo   [1/3] 首次运行，正在创建虚拟环境...
  python -m venv .venv
  if errorlevel 1 (
    echo   [x] 创建虚拟环境失败
    pause
    exit /b 1
  )

  echo   [2/3] 安装依赖，第一次大约 1-2 分钟...
  ".venv\Scripts\python.exe" -m pip install -q --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
  if errorlevel 1 (
    echo         直连失败，改用清华镜像重试...
    ".venv\Scripts\python.exe" -m pip install -q -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
  )
  if errorlevel 1 (
    echo   [x] 依赖安装失败，请检查网络后重试
    pause
    exit /b 1
  )
) else (
  echo   [1/3] 虚拟环境已就绪
)

echo   [2/3] 启动界面...
echo   [3/3] 浏览器会自动打开，地址见下方（端口被占用会自动换）
echo.
echo   关闭这个窗口即可停止服务。
echo.

".venv\Scripts\python.exe" -m xuanjqd preview
pause
