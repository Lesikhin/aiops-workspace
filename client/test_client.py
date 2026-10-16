"""
Тестовый клиент для проверки MCP-сервера и tool-calling цикла (FR-2.1..FR-2.5).

Запускает MCP-сервер как дочерний процесс через stdio, получает список
инструментов, отправляет запрос к локальной LLM (Ollama) и обрабатывает
цикл вызовов инструментов до получения финального ответа.

Запуск:
  cd d:\\ml\\aiops-workspace\\client
  uv run python test_client.py

Требования:
  - Ollama запущен (ollama serve)
  - Модель llama3.1:8b загружена (ollama pull llama3.1:8b) qwen2.5:7b - llama3.1:8b хреново работает
  - Qdrant запущен в Docker (docker ps | findstr qdrant)
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import ollama

# Путь к MCP-серверу (относительно этого файла)
SERVER_DIR = Path(__file__).parent.parent / "mcp_server"
SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "system_prompt.md"

# Модель LLM (согласована в ТЗ v1.2)
LLM_MODEL = "qwen2.5:7b"

# Тестовый запрос пользователя
TEST_QUERY = "Что происходит с order-service? Найди runbook для решения проблемы."


def build_tool_schemas(tools) -> list[dict]:
    """Формирует схему инструментов для Ollama из MCP-списка."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.inputSchema,
            },
        }
        for t in tools.tools
    ]


async def main() -> None:
    print("=" * 70)
    print("Тестовый клиент AIOps Workspace (tool-calling цикл)")
    print("=" * 70)

    # Загружаем системный промпт
    system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")

    # Подключаемся к MCP-серверу через stdio
    server_params = StdioServerParameters(
        command="uv",
        args=["--directory", str(SERVER_DIR), "run", "python", "server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()

            print("\nДоступные MCP-инструменты:")
            for t in tools.tools:
                print(f"  - {t.name}: {t.description.splitlines()[0]}")

            print(f"\nПользователь: {TEST_QUERY}")
            print("-" * 70)

            # Первый запрос к LLM
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": TEST_QUERY},
            ]

            response = ollama.chat(
                model=LLM_MODEL,
                messages=messages,
                tools=build_tool_schemas(tools),
            )

            message = response["message"]
            iteration = 0
            max_iterations = 10  # Защита от бесконечного цикла

            # Цикл обработки tool-calls
            while message.get("tool_calls") and iteration < max_iterations:
                iteration += 1
                print(f"\n[Итерация {iteration}] LLM вызывает инструменты:")

                # Добавляем сообщение ассистента в историю
                messages.append(
                    {
                        "role": "assistant",
                        "content": message.get("content") or "",
                        "tool_calls": message.get("tool_calls"),
                    }
                )

                # Выполняем каждый вызов инструмента
                for tc in message["tool_calls"]:
                    tool_name = tc["function"]["name"]
                    args = tc["function"]["arguments"]
                    tool_call_id = tc.get("id", f"call_{iteration}")

                    print(f"  -> {tool_name}({args})")

                    try:
                        result = await session.call_tool(tool_name, arguments=args)
                        result_text = result.content[0].text
                    except Exception as e:
                        result_text = f"Ошибка выполнения инструмента: {e}"
                        print(f"  !! Ошибка: {e}")

                    # Показываем усечённый результат
                    preview = result_text[:200].replace("\n", " ")
                    print(f"  <- результат: {preview}...")

                    # Добавляем результат в историю сообщений
                    messages.append(
                        {
                            "role": "tool",
                            "content": result_text,
                            "tool_call_id": tool_call_id,
                        }
                    )

                # Повторный запрос к LLM с результатами
                response = ollama.chat(
                    model=LLM_MODEL,
                    messages=messages,
                    tools=build_tool_schemas(tools),
                )
                message = response["message"]

            # Финальный ответ
            print("\n" + "=" * 70)
            print("ФИНАЛЬНЫЙ ОТВЕТ АССИСТЕНТА:")
            print("=" * 70)
            print(message.get("content", "(пустой ответ)"))
            print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nПрервано пользователем.")
        sys.exit(0)
    except Exception as e:
        print(f"\nКритическая ошибка: {e}", file=sys.stderr)
        sys.exit(1)