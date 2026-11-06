@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 宣讲会签到码

echo.
echo   宣讲会签到码
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

python -c "import fastapi, uvicorn, segno, PIL, rich, typer" >nul 2>nul
if errorlevel 1 (
  echo   [1/2] 缺少依赖，正在安装（只需要一次）...
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo         直连失败，改用清华镜像重试...
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
  )
  python -c "import fastapi" >nul 2>nul
  if errorlevel 1 (
    echo   [x] 依赖安装失败，请检查网络后重试
    pause
    exit /b 1
  )
) else (
  echo   [1/2] 依赖已就绪
)

echo   [2/2] 启动界面，浏览器会自动打开...
echo.
echo   关闭这个窗口即可停止服务。
echo.

python -m xuanjqd preview
pause
