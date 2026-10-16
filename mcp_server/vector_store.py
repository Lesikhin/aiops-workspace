"""
Модуль работы с векторным хранилищем Qdrant и эмбеддингами Ollama.

Отвечает за:
  - получение эмбеддингов через локальный Ollama (nomic-embed-text, 768 dim);
  - ленивую инициализацию коллекции knowledge_base (FR-1.10);
  - семантический поиск с опциональной фильтрацией по тегам (FR-1.5..FR-1.7);
  - принудительную переиндексацию (FR-1.11).

Все вызовы локальные: Qdrant (http://localhost:6333), Ollama (http://localhost:11434).
Данные не покидают периметр (NFR-1, NFR-2).
"""
from __future__ import annotations

from typing import Any

import ollama
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    PointStruct,
    VectorParams,
)

import mock_data

COLLECTION_NAME = "knowledge_base"
EMBEDDING_MODEL = "nomic-embed-text"
VECTOR_SIZE = 768
QDRANT_URL = "http://localhost:6333"

_client: QdrantClient | None = None


def get_client() -> QdrantClient:
    """Ленивое создание клиента Qdrant (один экземпляр на процесс)."""
    global _client
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL, timeout=10)
    return _client


def get_embedding(text: str) -> list[float]:
    """Получает векторное представление текста через локальный Ollama."""
    response = ollama.embeddings(model=EMBEDDING_MODEL, prompt=text)
    return response["embedding"]


def collection_exists() -> bool:
    """Проверяет наличие коллекции knowledge_base."""
    client = get_client()
    return any(c.name == COLLECTION_NAME for c in client.get_collections().collections)


def _build_points(documents: list[dict[str, Any]]) -> list[PointStruct]:
    """Готовит точки для загрузи: текст = title + content, метаданные = payload."""
    points: list[PointStruct] = []
    for idx, doc in enumerate(documents):
        text_for_embedding = f"{doc['title']}. {doc['content']}"
        points.append(
            PointStruct(
                id=idx,
                vector=get_embedding(text_for_embedding),
                payload={
                    "id": doc["id"],
                    "title": doc["title"],
                    "content": doc["content"],
                    "tags": doc["tags"],
                    "last_updated": doc["last_updated"],
                },
            )
        )
    return points


def _create_collection() -> None:
    """Создаёт коллекцию с косинусной метрикой и размером вектора 768."""
    get_client().create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )


def ensure_collection_initialized() -> None:
    """Ленивая инициализация: создаёт коллекцию и загружает данные, если их нет."""
    client = get_client()

    if not collection_exists():
        _create_collection()

    if client.count(collection_name=COLLECTION_NAME).count == 0:
        documents = mock_data.KNOWLEDGE_BASE
        if not documents:
            return
        print(f"[vector_store] Коллекция пуста. Индексирую {len(documents)} документов...")
        client.upsert(collection_name=COLLECTION_NAME, points=_build_points(documents))
        print("[vector_store] Индексация завершена.")


def _query(query_vector: list[float], search_filter: Filter | None, top_k: int) -> list:
    """
    Обёртка над поиском: использует современный query_points и откатывается
    на устаревший search() для совместимости со старыми версиями qdrant-client.
    """
    client = get_client()
    try:
        response = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=search_filter,
            limit=top_k,
            with_payload=True,
        )
        return response.points
    except AttributeError:
        return client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            query_filter=search_filter,
            limit=top_k,
            with_payload=True,
        )


def search_knowledge_base(
    query: str,
    tags: list[str] | None = None,
    top_k: int = 3,
) -> dict[str, Any]:
    """
    Семантический поиск по базе знаний (FR-1.5..FR-1.7).

    Args:
        query: поисковый запрос.
        tags: опциональная фильтрация по тегам.
        top_k: количество возвращаемых документов.

    Returns:
        {"results": [...], "total_found": N} — результаты с полем _score (cosine).
    """
    ensure_collection_initialized()

    query_vector = get_embedding(query)

    search_filter = None
    if tags:
        search_filter = Filter(
            must=[FieldCondition(key="tags", match=MatchAny(any=tags))]
        )

    matches = _query(query_vector, search_filter, top_k)

    results = [
        {**point.payload, "_score": round(float(point.score), 4)}
        for point in matches
    ]
    return {"results": results, "total_found": len(results)}


def reindex_knowledge_base(documents: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """
    Принудительная переиндексация (FR-1.11).

    Args:
        documents: список статей. По умолчанию берётся из mock_data.KNOWLEDGE_BASE.

    Returns:
        {"status": "success", "indexed_count": N}
    """
    if documents is None:
        documents = mock_data.KNOWLEDGE_BASE

    client = get_client()
    if collection_exists():
        client.delete_collection(COLLECTION_NAME)

    _create_collection()
    client.upsert(collection_name=COLLECTION_NAME, points=_build_points(documents))
    return {"status": "success", "indexed_count": len(documents)}


if __name__ == "__main__":
    # Быстрый smoke-тест модуля: python vector_store.py
    print("Проверка связи с Qdrant:", get_client().get_collections())
    print("Пример эмбеддинга (первые 5 измерений):", get_embedding("test")[:5])
    print("Поиск 'high cpu order-service':")
    for item in search_knowledge_base("high cpu order-service")["results"]:
        print(f"  {item['id']} | score={item['_score']} | {item['title']}")