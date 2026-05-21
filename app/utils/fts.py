"""SQLite FTS5 full-text search utilities."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


async def search_comments_fts(
    db: AsyncSession,
    task_id: int,
    query: str,
    min_score: float = 0.0,
    min_likes: int = 0,
    actionable_only: bool = False,
    sort: str = "score",
    page: int = 1,
    per_page: int = 50,
):
    """Full-text search across comments using FTS5."""
    conditions = ["c.task_id = :task_id", "c.usefulness_score >= :min_score"]
    params = {
        "task_id": task_id,
        "min_score": min_score,
        "min_likes": min_likes,
        "offset": (page - 1) * per_page,
        "limit": per_page,
    }

    if query:
        # Sanitize FTS5 query: escape special chars, add prefix matching
        sanitized = " ".join(
            f'"{word}"*' if word else ""
            for word in query.strip().split()
            if word
        )
        if sanitized:
            conditions.append("comments_fts MATCH :fts_query")
            params["fts_query"] = sanitized

    if min_likes > 0:
        conditions.append("c.liked_count >= :min_likes")

    if actionable_only:
        conditions.append("c.is_actionable = 1")

    where_clause = " AND ".join(conditions)

    # Count
    count_sql = f"""
    SELECT COUNT(*) FROM comments c
    {"JOIN comments_fts ON comments_fts.rowid = c.id" if query else ""}
    WHERE {where_clause}
    """
    result = await db.execute(text(count_sql), params)
    total = result.scalar() or 0

    # Results
    if sort == "likes":
        order = "c.liked_count DESC"
    elif sort == "date":
        order = "c.created_at DESC"
    else:
        order = "usefulness_score DESC, c.liked_count DESC"

    fts_join = "JOIN comments_fts ON comments_fts.rowid = c.id" if query else ""
    select_sql = f"""
    SELECT c.*, comments_fts.rank
    FROM comments c
    {fts_join}
    WHERE {where_clause}
    ORDER BY {order}
    LIMIT :limit OFFSET :offset
    """
    result = await db.execute(text(select_sql), params)
    rows = result.fetchall()

    return rows, total
