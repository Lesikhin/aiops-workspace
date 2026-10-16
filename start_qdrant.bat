@echo off
chcp 65001 >nul
echo Запуск Qdrant в Docker-контейнере...
docker run -d -p 6333:6333 -p 6334:6334 -v qdrant_storage:/qdrant/storage --name qdrant qdrant/qdrant
echo Qdrant запущен. Панель управления доступна по адресу: http://localhost:6333/dashboard
pause