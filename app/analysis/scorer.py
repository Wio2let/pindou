"""Comment usefulness scoring engine.

Scores comments on a 0.0-1.0 scale using heuristic signals:
- Engagement (likes, replies)
- Keyword matches
- User quality indicators
- Content quality (length, structure)

Fully local — no external API calls needed for the heuristic scorer.
"""

import math
import re
from typing import Optional
from app.analysis.patterns import is_actionable, count_actionable_matches


class CommentAnalyzer:
    """Analyzes and scores comments for usefulness.

    Uses a weighted heuristic model to produce a 0.0-1.0 score.
    Designed to run locally without any external API dependency.
    """

    WEIGHTS = {
        "engagement": 0.35,
        "keyword_match": 0.30,
        "user_quality": 0.15,
        "content_quality": 0.20,
    }

    def score(
        self,
        comment: dict,
        task_keywords: Optional[list[str]] = None,
        min_likes: int = 1,
    ) -> float:
        """Calculate usefulness score for a single comment.

        Args:
            comment: Comment data dict with fields:
                liked_count, sub_comment_count, content, avatar,
                ip_location, user_name
            task_keywords: List of keywords to match against content
            min_likes: Minimum likes threshold for engagement scoring

        Returns:
            Float score from 0.0 to 1.0
        """
        content = comment.get("content", "") or ""
        if not content.strip():
            return 0.0

        scores = {
            "engagement": self._score_engagement(comment),
            "keyword_match": self._score_keyword_match(content, task_keywords or []),
            "user_quality": self._score_user_quality(comment),
            "content_quality": self._score_content_quality(content),
        }

        # Weighted sum
        total = sum(
            scores[k] * self.WEIGHTS[k] for k in self.WEIGHTS if k in scores
        )

        # Penalties
        # Very short comments are rarely useful
        if len(content) < 10:
            total *= 0.5
        # Comments with only emojis/stickers
        if self._is_low_effort(content):
            total *= 0.3

        return round(min(total, 1.0), 2)

    def classify(self, score: float) -> str:
        """Classify score into a human-readable label."""
        if score >= 0.7:
            return "high"
        elif score >= 0.4:
            return "medium"
        elif score > 0.0:
            return "low"
        return "unscored"

    def _score_engagement(self, comment: dict) -> float:
        """Score based on likes and replies (0.0-0.4)."""
        likes = int(comment.get("liked_count", 0))
        replies = int(comment.get("sub_comment_count", 0))

        if likes == 0 and replies == 0:
            return 0.0

        # Log scale: 1 like = ~0.17, 10 = ~0.26, 100 = ~0.35, 1000 = 0.4
        like_score = min(0.065 * math.log(max(likes, 1) + 1), 0.30)
        reply_score = min(0.03 * math.log(max(replies, 1) + 1), 0.10)

        return min(like_score + reply_score, 0.4)

    def _score_keyword_match(
        self, content: str, keywords: Optional[list[str]]
    ) -> float:
        """Score based on keyword matches (0.0-0.3)."""
        if not keywords:
            return 0.0

        matches = 0
        for kw in keywords:
            if not kw.strip():
                continue
            if kw.strip().lower() in content.lower():
                matches += 1

        if matches == 0:
            return 0.0

        return min(matches / len(keywords), 0.3)

    def _score_user_quality(self, comment: dict) -> float:
        """Score based on user quality signals (0.0-0.15)."""
        score = 0.0

        # Has avatar
        if comment.get("avatar"):
            score += 0.05

        # Has IP location
        if comment.get("ip_location"):
            score += 0.04

        # Has sub-comments (others engaged with this comment)
        if int(comment.get("sub_comment_count", 0)) > 0:
            score += 0.04

        # Has a non-default username (not "user12345" format)
        user_name = comment.get("user_name", "") or ""
        if user_name and not re.match(r"^用户\d+$", user_name):
            score += 0.02

        return min(score, 0.15)

    def _score_content_quality(self, content: str) -> float:
        """Score based on content length and structure (0.0-0.2)."""
        length = len(content)

        # Ideal length: 30-500 Chinese characters
        if 30 <= length <= 500:
            return 0.20
        elif 10 <= length < 30:
            return 0.10
        elif length > 500:
            return 0.15  # Long but might be rambling
        return 0.0

    def _is_low_effort(self, content: str) -> bool:
        """Detect low-effort content (emojis only, single word, etc.)."""
        text_only = re.sub(r"[^一-鿿\w]", "", content)
        if not text_only:
            return True
        # Single character responses
        if len(text_only) <= 1:
            return True
        return False

    def extract_matched_keywords(
        self, content: str, keywords: Optional[list[str]]
    ) -> list[str]:
        """Return which keywords were found in content."""
        if not keywords:
            return []
        return [
            kw.strip()
            for kw in keywords
            if kw.strip() and kw.strip().lower() in content.lower()
        ]

    def is_actionable(self, content: str) -> bool:
        """Check if comment contains actionable info (delegates to patterns)."""
        return is_actionable(content)
