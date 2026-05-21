from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event
from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.database_url,
    echo=settings.log_level == "DEBUG",
    connect_args={
        "check_same_thread": False,
    },
)


@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable WAL mode and FTS5 support."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _add_column_if_missing(conn, table: str, column: str, ddl: str):
    """SQLite ALTER TABLE ADD COLUMN, idempotent across restarts."""
    rows = (await conn.exec_driver_sql(f"PRAGMA table_info({table})")).fetchall()
    if column in {r[1] for r in rows}:
        return
    await conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create all tables and FTS5 indexes."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Lightweight migrations: ADD COLUMN for fields added after release.
    async with engine.begin() as conn:
        await _add_column_if_missing(
            conn, "monitor_tasks", "min_post_likes", "INTEGER DEFAULT 0"
        )
        await _add_column_if_missing(
            conn, "comments", "pictures", "TEXT DEFAULT '[]'"
        )
        await _add_column_if_missing(
            conn, "monitor_tasks", "publish_time_type", "INTEGER DEFAULT 0"
        )
        await _add_column_if_missing(
            conn, "comments", "favorite", "INTEGER DEFAULT 0"
        )
        await _add_column_if_missing(
            conn, "comments", "category", "VARCHAR(120) DEFAULT ''"
        )
        # Index for fast favorites/category queries
        await conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_comments_favorite "
            "ON comments(favorite, category)"
        )

    # Create FTS5 virtual table for comment full-text search
    async with engine.begin() as conn:
        await conn.exec_driver_sql(
            "CREATE VIRTUAL TABLE IF NOT EXISTS comments_fts USING fts5("
            "content,"
            "content=comments,"
            "content_rowid=id"
            ")"
        )

        # Triggers to keep FTS index in sync
        await conn.exec_driver_sql(
            "CREATE TRIGGER IF NOT EXISTS comments_ai AFTER INSERT ON comments BEGIN "
            "INSERT INTO comments_fts(rowid, content) VALUES (new.id, new.content); "
            "END"
        )
        await conn.exec_driver_sql(
            "CREATE TRIGGER IF NOT EXISTS comments_ad AFTER DELETE ON comments BEGIN "
            "INSERT INTO comments_fts(comments_fts, rowid, content) "
            "VALUES('delete', old.id, old.content); "
            "END"
        )
        await conn.exec_driver_sql(
            "CREATE TRIGGER IF NOT EXISTS comments_au AFTER UPDATE ON comments BEGIN "
            "INSERT INTO comments_fts(comments_fts, rowid, content) "
            "VALUES('delete', old.id, old.content); "
            "INSERT INTO comments_fts(rowid, content) VALUES (new.id, new.content); "
            "END"
        )
