@echo off
chcp 65001 >nul
echo Запуск тестового клиента (Tool-calling цикл)...
cd /d "%~dp0client"
uv run python test_client.py
pause