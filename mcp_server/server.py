"""
MCP-сервер для AIOps-workspace (ТЗ v1.2).

Предоставляет LLM три инструмента:
  - get_system_status      : read-only статус инфраструктуры (имитация Prometheus)
  - search_knowledge_base  : семантический поиск по runbook'ам через Qdrant
  - reindex_knowledge_base : принудительная переиндексация базы знаний

Транспорт: stdio (стандарт для локальных инструментов, без открытых портов).
Все операции read-only — write-операции реализованы в PoC #4 с HITL.
"""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

import mock_data
import vector_store

# Инициализация MCP-сервера (без аргумента version для совместимости с mcp 1.x)
mcp = FastMCP("aiops-workspace")


@mcp.tool()
def get_system_status(service_name: str | None = None) -> dict[str, Any]:
    """
    Получить текущий статус инфраструктуры (имитация Prometheus/Grafana).

    Args:
        service_name: имя сервиса (например, 'payment-gateway', 'order-service',
                      'user-db-primary', 'kafka-cluster').
                      Если None — возвращает краткую сводку по всем сервисам.

    Returns:
        JSON со статусом сервиса: status, cpu_percent, memory_percent,
        error_rate_5m, owner_team, active_alerts и др.
        Если сервис не найден — возвращает {"error": ..., "available_services": [...]}.
    """
    if service_name is None:
        return {
            "summary": {
                name: {"status": s["status"], "owner_team": s["owner_team"]}
                for name, s in mock_data.SYSTEMS_STATUS.items()
            },
            "hint": "Укажите service_name для детальной информации.",
        }

    service = mock_data.SYSTEMS_STATUS.get(service_name)
    if service is None:
        return {
            "error": f"Service '{service_name}' not found",
            "available_services": list(mock_data.SYSTEMS_STATUS.keys()),
        }
    return service


@mcp.tool()
def search_knowledge_base(
    query: str,
    tags: list[str] | None = None,
    top_k: int = 3,
) -> dict[str, Any]:
    """
    Семантический (векторный) поиск по базе знаний через Qdrant.

    Использует модель эмбеддингов nomic-embed-text (768 dim) и косинусное сходство.
    При первом вызове автоматически инициализирует коллекцию (ленивая загрузка).

    Args:
        query: поисковый запрос (например, 'high cpu order-service').
        tags: опциональная фильтрация по тегам (например, ['order-service', 'cpu']).
        top_k: количество возвращаемых статей (по умолчанию 3).

    Returns:
        {"results": [...], "total_found": N}, где каждый результат содержит:
        id, title, content, tags, last_updated, _score (cosine similarity).
    """
    return vector_store.search_knowledge_base(query=query, tags=tags, top_k=top_k)


@mcp.tool()
def reindex_knowledge_base() -> dict[str, Any]:
    """
    Принудительно переиндексировать базу знаний.

    Использовать при изменении mock_data.KNOWLEDGE_BASE или после ручного
    обновления источников знаний. Пересоздаёт коллекцию и заново вычисляет
    эмбеддинги для всех статей.

    Returns:
        {"status": "success", "indexed_count": N}
    """
    return vector_store.reindex_knowledge_base(mock_data.KNOWLEDGE_BASE)


if __name__ == "__main__":
    # Запуск сервера в stdio-режиме (стандарт для Open WebUI / Claude Desktop / MCP Inspector)
    mcp.run(transport="stdio")