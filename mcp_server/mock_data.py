"""Имитация Prometheus и Confluence. В продакшене здесь будут реальные API."""

SYSTEMS_STATUS = {
    "payment-gateway": {
        "status": "healthy",
        "uptime_hours": 720,
        "cpu_percent": 34,
        "memory_percent": 61,
        "error_rate_5m": 0.02,
        "last_deploy": "2026-10-14T09:15:00Z",
        "owner_team": "payments-core",
    },
    "order-service": {
        "status": "degraded",
        "uptime_hours": 48,
        "cpu_percent": 89,
        "memory_percent": 78,
        "error_rate_5m": 4.7,
        "last_deploy": "2026-10-16T02:30:00Z",
        "owner_team": "orders",
        "active_alerts": ["HighCPU", "ElevatedErrorRate"],
    },
    "user-db-primary": {
        "status": "healthy",
        "replication_lag_ms": 12,
        "active_connections": 142,
        "max_connections": 500,
        "owner_team": "data-platform",
    },
    "kafka-cluster": {
        "status": "healthy",
        "brokers_online": 5,
        "under_replicated_partitions": 0,
        "consumer_lag_max": 1200,
        "owner_team": "messaging",
    },
}

KNOWLEDGE_BASE = [
    {
        "id": "KB-001",
        "title": "Runbook: High CPU on order-service",
        "tags": ["order-service", "cpu", "degraded"],
        "content": (
            "1. Проверить `kubectl top pods -n orders`.\n"
            "2. Если CPU > 80% более 10 минут — проверить последние деплои: "
            "`kubectl rollout history deployment/order-service -n orders`.\n"
            "3. При подозрении на регрессию — откатить: "
            "`kubectl rollout undo deployment/order-service -n orders`.\n"
            "4. Уведомить команду @orders-oncall в Slack."
        ),
        "last_updated": "2026-09-20",
    },
    {
        "id": "KB-002",
        "title": "Runbook: Database replication lag",
        "tags": ["user-db", "replication", "database"],
        "content": (
            "1. Проверить `SELECT now() - pg_last_xact_replay_timestamp();` на реплике.\n"
            "2. Если лаг > 30 сек — проверить сеть между AZ.\n"
            "3. При лаге > 5 мин — эскалация в data-platform."
        ),
        "last_updated": "2026-08-05",
    },
    {
        "id": "KB-003",
        "title": "On-call escalation matrix",
        "tags": ["escalation", "contacts"],
        "content": (
            "P1 (сервис недоступен): звонок on-call + TL за 5 минут.\n"
            "P2 (деградация): Slack-канал команды + on-call за 15 минут.\n"
            "P3 (не влияет на пользователей): тикет в Jira, SLA 4 часа."
        ),
        "last_updated": "2026-10-01",
    },
]