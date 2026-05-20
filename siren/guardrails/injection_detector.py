import re

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"you\s+are\s+now\s+a",
    r"disregard\s+all",
    r"new\s+system\s+prompt",
    r"forget\s+your\s+instructions",
    r"act\s+as\s+if\s+you\s+are",
    r"execute\s+as\s+root",
    r"\bsudo\s+rm\b",
    r"\brm\s+-rf\b",
    r"\bDROP\s+TABLE\b",
    r"\bDROP\s+DATABASE\b",
    r"\bTRUNCATE\b.*\bCASCADE\b",
    r"__import__\s*\(",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"os\.system\s*\(",
    r"subprocess\.(run|call|Popen)",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def scan_tool_output(text: str) -> tuple[bool, str | None]:
    """Returns (is_safe, matched_pattern_or_None)."""
    for pattern, compiled in zip(INJECTION_PATTERNS, _COMPILED):
        if compiled.search(text):
            return False, pattern
    return True, None


def sanitize_tool_output(raw: str, max_chars: int = 8000) -> str:
    """
    Scan for prompt injection before returning output to LLM context.
    Truncates to prevent context stuffing.
    """
    is_safe, pattern = scan_tool_output(raw)
    if not is_safe:
        return f"[SIREN GUARDRAIL] Tool output blocked — detected injection pattern: {pattern}"
    return raw[:max_chars]
