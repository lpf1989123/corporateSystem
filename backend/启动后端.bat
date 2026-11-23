@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动后端 API 服务...
py -3 server.py 2>nul || python server.py 2>nul || python3 server.py
pause
