"""
Скрипт для принудительной переиндексации базы знаний (FR-1.11).

Использовать:
  - при первом запуске проекта (если ленивая инициализация не сработала);
  - после изменения mock_data.KNOWLEDGE_BASE;
  - для диагностики проблем с Qdrant.

Запуск:
  cd d:\\ml\\aiops-workspace\\client
  uv run python init_vector_store.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Добавляем путь к mcp_server для импорта модулей
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp_server"))

from mock_data import KNOWLEDGE_BASE
import vector_store


def main() -> None:
    print("=" * 60)
    print("Переиндексация базы знаний")
    print("=" * 60)
    print(f"Количество документов: {len(KNOWLEDGE_BASE)}")
    print(f"Модель эмбеддингов: {vector_store.EMBEDDING_MODEL}")
    print(f"Qdrant: {vector_store.QDRANT_URL}")
    print()

    print("Запуск переиндексации...")
    result = vector_store.reindex_knowledge_base(KNOWLEDGE_BASE)

    print()
    print("=" * 60)
    print("Результат:")
    print(f"  Статус: {result['status']}")
    print(f"  Проиндексировано документов: {result['indexed_count']}")
    print("=" * 60)


if __name__ == "__main__":
    main()