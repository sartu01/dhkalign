# Minimal GPT adapter skeleton (WRAITH)
# Returns None if no provider/secret configured. Real calls should be added later.
import os
from typing import Optional

PROVIDER = os.getenv("GPT_PROVIDER", "openai").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

def translate(text: str, src_lang: str, tgt_lang: str) -> Optional[str]:
    """Return translated text or None if not configured.
    NOTE: Edge already implements GPT fallback. This backend stub is a no-op placeholder.
    """
    return None
