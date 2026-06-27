@echo off
chcp 65001 >nul
echo.
echo ╔════════════════════════════════════╗
echo ║    🌍 中东每日简报 启动中...     ║
echo ╚════════════════════════════════════╝
echo.

REM 尝试自动查找 Python
for %%p in (python python3 py) do (
    where %%p >nul 2>&1 && set "PYTHON=%%p" && goto :found
)
echo [错误] 未找到 Python，请安装 Python 3.10+
pause
exit /b 1

:found
echo [OK] 使用 Python: %PYTHON%
set "DIR=d:\Boeker 1.0\middle-east-dashboard"
cd /d "%DIR%"

echo [1/2] 抓取新闻源并生成日报...
"%PYTHON%" -X utf8 main.py --fetch

echo.
echo [2/2] 打开日报...
start "" "output\index.html"

echo.
echo ==========================================
echo  完成！日报已生成在 output\index.html
echo ==========================================
pause
