"""LLM synthesis — optional, falls back to extraction if no API key."""

import logging

from app.config import settings

logger = logging.getLogger(__name__)


def synthesize(query: str, chunks: list[dict], session_context: list[dict] | None = None) -> str:
    """Synthesize an answer from retrieved chunks using available LLM.

    Falls back to a structured extraction if no LLM key is configured.
    """
    # Build context string from chunks
    context_parts = []
    for i, chunk in enumerate(chunks):
        source = chunk.get("source", "unknown")
        text = chunk.get("text", "")
        context_parts.append(f"[Source {i + 1}: {source}]\n{text}")
    context_str = "\n\n".join(context_parts)

    # Add session history if available
    session_str = ""
    if session_context:
        history = []
        for turn in session_context[-5:]:  # Last 5 turns
            history.append(f"Q: {turn['query']}\nA: {turn['answer'][:200]}")
        session_str = "Previous conversation:\n" + "\n".join(history) + "\n\n"

    prompt = f"""{session_str}Based on the following sources, answer the query accurately. Cite sources by number. If the sources don't contain enough information, say so.

Sources:
{context_str}

Query: {query}

Answer:"""

    # Try Anthropic first
    if settings.anthropic_api_key:
        try:
            return _call_anthropic(prompt)
        except Exception as e:
            logger.warning(f"Anthropic synthesis failed: {e}")

    # Try OpenAI
    if settings.openai_api_key:
        try:
            return _call_openai(prompt)
        except Exception as e:
            logger.warning(f"OpenAI synthesis failed: {e}")

    # Fallback: structured extraction (no LLM)
    return _fallback_synthesis(query, chunks)


def _call_anthropic(prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def _call_openai(prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
    )
    return response.choices[0].message.content


def _fallback_synthesis(query: str, chunks: list[dict]) -> str:
    """No-LLM fallback: return top chunks as a structured summary."""
    if not chunks:
        return "No relevant information found in the knowledge base."

    lines = [f"Found {len(chunks)} relevant source(s) for: \"{query}\"\n"]
    for i, chunk in enumerate(chunks[:5]):
        source = chunk.get("source", "unknown")
        score = chunk.get("score", 0)
        text = chunk.get("text", "")[:300]
        lines.append(f"**[Source {i + 1}]** ({source}, relevance: {score:.2f})")
        lines.append(f"{text}...")
        lines.append("")

    lines.append("_Note: Add ANTHROPIC_API_KEY or OPENAI_API_KEY for AI-synthesized answers._")
    return "\n".join(lines)
