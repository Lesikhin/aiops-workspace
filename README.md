# AIOps Workspace 

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-1.x-000000?style=flat-square)](https://modelcontextprotocol.io/)
[![Qdrant](https://img.shields.io/badge/Qdrant-Docker-DD3929?style=flat-square&logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![Ollama](https://img.shields.io/badge/Ollama-Local-000000?style=flat-square&logo=ollama&logoColor=white)](https://ollama.com/)
[![LLM](https://img.shields.io/badge/LLM-qwen2.5%3A7b-F59E0B?style=flat-square)](https://ollama.com/library/qwen2.5)
[![Embeddings](https://img.shields.io/badge/Embeddings-nomic--embed--text-7C3AED?style=flat-square)](https://ollama.com/library/nomic-embed-text)
[![Transport](https://img.shields.io/badge/Transport-stdio-10B981?style=flat-square)](https://modelcontextprotocol.io/specification)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

Локальный AI-ассистент инженера эксплуатации с MCP-интеграцией, векторным поиском (Qdrant) и локальной LLM. Проект демонстрирует архитектурный подход к безопасному применению AI в промышленном контуре с фокусом на решение проблемы галлюцинаций.

## 1. Бизнес-проблема и решение

**Проблема**: Инженеры L1/L2 тратят 15 минут на поиск runbook'ов в Confluence, Jira и голове. При этом LLM-ассистенты без строгой интеграции с источниками данных генерируют правдоподобные, но ложные инструкции (галлюцинации), что в AIOps-контексте ведет к ложным действиям и увеличению MTTR.

**Решение**: Построен локальный AI-ассистент, который:
- Не отвечает без обращения к инструментам (MCP-протокол).
- Использует векторный поиск по актуальным runbook'ам (Qdrant + nomic-embed-text).
- Работает полностью локально — данные не покидают периметр.
- Требует явного подтверждения для write-операций (в PoC #4).

**Измеримый результат**: Тестирование показало снижение галлюцинаций в метриках с ~40% (базовая llama3.1:8b) до 0% (qwen2.5:7b) при сохранении 100% точности tool-calling.

## 2. Архитектура
+-----------------------------------------------------------------+
| Пользователь                                                    |
| (Open WebUI / CLI-клиент / MCP Inspector)                       |
+-----------------------------------------------------------------+
                              |
                              v
+-----------------------------------------------------------------+
| LLM (Ollama, qwen2.5:7b)                                        | 
| + System Prompt с guardrails (FR-3.1..FR-3.3)                   |
+-----------------------------------------------------------------+
                              | 
                              v
+-----------------------------------------------------------------+
| MCP-сервер (stdio-транспорт)                                    |
| +------------------+ +------------------+ +-------------------+ |
| | get_system_status| | search_knowledge | | reindex_kb        | |
| | (mock_data.py)   | | _base            | |                   | |
| +------------------+ +--------+---------+ +-----------------+ | |
+-----------------------------------------------------------------+
                                |
                  +-------------+-------------+
                  v                           v
+-----------------------+       +-----------------------+
| Qdrant (Docker)       |       | Ollama Embeddings     |
| localhost:6333        |       | nomic-embed-text      |
| knowledge_base        |       | (768 dim, cosine)     |
+-----------------------+       +-----------------------+

## 3. Ключевое инженерное решение: борьба с галлюцинациями

В ходе реализации была выявлена и решена проблема "lazy tool-calling": базовые модели (llama3.1:8b) эмулируют вызов инструмента текстом вместо реального обращения к API, генерируя правдоподобные, но ложные метрики (например, CPU 83.21% вместо реальных 89%).

**Архитектурное решение**:
1. **Смена модели**: переход на qwen2.5:7b, заточенную под агентные задачи.
2. **Усиление промпта**: явный запрет на использование знаний из памяти о runbook'ах.
3. **Обязательное цитирование**: требование указывать только источники, возвращенные инструментами.

Результат — 100% точность tool-calling и полное отсутствие галлюцинаций в метриках.

## 4. Стек технологий

| Компонент                 | Технология             | Назначение                     |
|---------------------------|------------------------|--------------------------------|
| Язык                      | Python 3.11+           | Основная реализация            |
| Управление зависимостями  | uv                     | Современная замена pip         |
| MCP SDK                   | mcp[cli] < 2.0.0       | Реализация MCP-сервера         |
| Векторная БД              | Qdrant (Docker)        | Хранение эмбеддингов           |
| Qdrant-клиент             | qdrant-client >= 1.7.0 | Python SDK для Qdrant          |
| LLM                       | Ollama                 | Локальный inference            |
| Модель LLM                | qwen2.5:7b             | Tool-calling, генерация        |
| Модель эмбеддингов        | nomic-embed-text       | Векторизация текстов (768 dim) |
| LLM-клиент                | ollama >= 0.4.0        | Python SDK для Ollama          |

## 5. Быстрый старт

### 5.1. Предварительные требования

- Python 3.11+
- Docker Desktop (для Qdrant)
- Ollama (для локальной LLM)
- uv (менеджер зависимостей)

### 5.2. Установка

```powershell
# Клонирование репозитория
git clone <repo-url>
cd aiops-workspace

# Установка зависимостей
uv sync

# Запуск Qdrant
docker run -d -p 6333:6333 -p 6334:6334 -v qdrant_storage:/qdrant/storage --name qdrant qdrant/qdrant

# Загрузка моделей Ollama
ollama pull qwen2.5:7b
ollama pull nomic-embed-text

# Инициализация векторного хранилища
uv run python client/init_vector_store.py