"""Regex patterns for detecting actionable content in comments."""

import re

# Actionable content patterns — comments matching these are likely
# to contain practical, useful information.
ACTIONABLE_PATTERNS = [
    # Recommendations
    (r"推荐|建议|种草|安利|强推", "recommendation"),
    # Comparisons
    (r"对比|比较|vs|还是|哪个好|区别", "comparison"),
    # Warnings
    (r"避雷|踩雷|注意|小心|别买|慎入|雷区", "warning"),
    # Results / effects
    (r"效果|变化|改善|坚持|用了|体验", "experience"),
    # Price / value
    (r"价格|性价比|便宜|贵|值不|值得|优惠|折扣", "price"),
    # Ingredients / materials
    (r"成分|配方|材质|质量|面料", "quality"),
    # Alternatives
    (r"代替|平替|替代|同款|类似", "alternative"),
    # Tutorials / methods
    (r"教程|方法|步骤|经验|技巧|分享|攻略", "tutorial"),
    # Specific numbers (dosages, durations, prices)
    (r"\d+[元块天次mlgkg]", "specific_info"),
    # Questions answered
    (r"用了|买了|去过|吃过", "firsthand_experience"),
]


def is_actionable(content: str) -> bool:
    """Check if comment text contains actionable information."""
    for pattern, _ in ACTIONABLE_PATTERNS:
        if re.search(pattern, content):
            return True
    return False


def get_actionable_types(content: str) -> list[str]:
    """Return all actionable categories matched in content."""
    matched = []
    for pattern, category in ACTIONABLE_PATTERNS:
        if re.search(pattern, content):
            matched.append(category)
    return matched


def count_actionable_matches(content: str) -> int:
    """Count how many actionable patterns are matched."""
    return sum(1 for pattern, _ in ACTIONABLE_PATTERNS if re.search(pattern, content))
