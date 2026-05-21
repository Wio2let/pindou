"""Optional LLM-based comment analysis.

Extends the heuristic scorer with semantic understanding.
Can use local Ollama (Qwen2.5, etc.) or remote API (DeepSeek, GLM, etc.).

This is OPTIONAL and only activated when configured.
"""

import json
from typing import Optional


class LLMCommentAnalyzer:
    """LLM-enhanced comment analysis.

    Uses a language model to evaluate comment usefulness semantically.
    Falls back to heuristic scores if LLM is unavailable.
    """

    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        self.api_url = api_url
        self.api_key = api_key

    async def analyze(
        self,
        comment_content: str,
        post_topic: str = "",
    ) -> dict:
        """Analyze a comment using LLM for semantic usefulness.

        Returns:
            dict with keys: usefulness (1-5), reason, category
        """
        if not self.api_url:
            return self._fallback()

        # TODO: Integrate with Ollama or OpenAI-compatible API
        # prompt = f"""你是一个小红书评论分析助手。请分析这条评论是否对关注「{post_topic}」的用户有用。
        #
        # 评论内容: "{comment_content}"
        #
        # 判断标准：
        # 1. 是否包含具体的推荐或建议
        # 2. 是否包含产品/服务的对比
        # 3. 是否包含个人真实体验
        # 4. 是否包含价格、成分等实用信息
        # 5. 是否包含避雷/警告信息
        #
        # 请返回JSON格式：
        # {{"usefulness": 1-5, "reason": "简短原因", "category": "推荐|对比|体验|价格|避雷|其他"}}
        # """
        #
        # response = await self._call_llm(prompt)
        # return json.loads(response)

        return self._fallback()

    def _fallback(self) -> dict:
        return {
            "usefulness": 3,
            "reason": "LLM not configured",
            "category": "other",
        }

    @property
    def is_configured(self) -> bool:
        return bool(self.api_url)
