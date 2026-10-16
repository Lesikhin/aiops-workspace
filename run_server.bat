@echo off
chcp 65001 >nul
echo Запуск MCP-сервера в режиме разработки (MCP Inspector)...
cd /d "%~dp0mcp_server"
uv run mcp dev server.py
pause