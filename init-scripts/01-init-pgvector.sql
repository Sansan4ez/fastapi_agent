-- Создание расширения pgvector для работы с векторными embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Проверка установки расширения
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
