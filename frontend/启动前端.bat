@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动前端静态服务...
py -3 serve.py 2>nul || python serve.py 2>nul || python3 serve.py
pause
