"""
Пример использования pgvector в SQLAlchemy для хранения embeddings
"""

from sqlalchemy import Column, Integer, String, Text
from pgvector.sqlalchemy import Vector
from app.database import Base


class KnowledgeBaseArticle(Base):
    """
    Пример модели для хранения статей базы знаний с векторными embeddings
    для семантического поиска
    """
    __tablename__ = 'knowledge_base_articles'

    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100))

    # Векторное представление для OpenAI text-embedding-3-small (1536 размерность)
    # или text-embedding-3-large (3072 размерность)
    embedding = Column(Vector(1536))


class ConversationHistory(Base):
    """
    Пример хранения истории разговоров с embeddings для контекстного поиска
    """
    __tablename__ = 'conversation_history'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    message = Column(Text, nullable=False)
    response = Column(Text)

    # Embedding сообщения для семантического поиска по истории
    message_embedding = Column(Vector(1536))


# Пример использования в коде:

async def create_article_with_embedding(session, title: str, content: str, embedding_vector: list):
    """
    Создание статьи с embedding

    Args:
        session: AsyncSession
        title: Заголовок статьи
        content: Содержание статьи
        embedding_vector: Список float значений (например, из OpenAI API)
    """
    article = KnowledgeBaseArticle(
        title=title,
        content=content,
        embedding=embedding_vector  # pgvector автоматически конвертирует list в vector
    )
    session.add(article)
    await session.commit()
    return article


async def find_similar_articles(session, query_embedding: list, limit: int = 5):
    """
    Поиск похожих статей используя косинусное расстояние

    Args:
        session: AsyncSession
        query_embedding: Embedding запроса
        limit: Количество результатов

    Returns:
        Список похожих статей, отсортированных по релевантности
    """
    from sqlalchemy import select, func

    # Используем косинусное расстояние для поиска похожих векторов
    # Меньшее расстояние = более похожие вектора
    stmt = (
        select(
            KnowledgeBaseArticle,
            KnowledgeBaseArticle.embedding.cosine_distance(query_embedding).label('distance')
        )
        .order_by('distance')
        .limit(limit)
    )

    result = await session.execute(stmt)
    return result.all()


async def find_similar_by_l2_distance(session, query_embedding: list, limit: int = 5):
    """
    Альтернативный метод поиска используя L2 расстояние (Euclidean)
    """
    from sqlalchemy import select

    stmt = (
        select(
            KnowledgeBaseArticle,
            KnowledgeBaseArticle.embedding.l2_distance(query_embedding).label('distance')
        )
        .order_by('distance')
        .limit(limit)
    )

    result = await session.execute(stmt)
    return result.all()


# Для создания индекса выполните SQL (через alembic миграцию):
#
# Индекс IVFFlat для быстрого приближенного поиска (для больших объемов данных):
# CREATE INDEX ON knowledge_base_articles USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
#
# Или индекс HNSW (Hierarchical Navigable Small World) - более быстрый и точный:
# CREATE INDEX ON knowledge_base_articles USING hnsw (embedding vector_cosine_ops);
#
# Для L2 расстояния используйте vector_l2_ops вместо vector_cosine_ops
