"""S5 PII sanitization for everything that is NOT the case record itself: application logs, chat memory,
feedback text, LangSmith traces. The case documents and the AI review stay complete (staff-only, audited).

Patterns: SSN, dates of birth, phone, email, member IDs, NPI, street addresses; plus the member and
provider names the AI review extracted for that case (exact-name redaction).
"""
import logging
import re

PATTERNS = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN]"),
    (re.compile(r"\b(0?[1-9]|1[0-2])[/-](0?[1-9]|[12]\d|3[01])[/-](19|20)\d{2}\b"), "[DATE]"),
    (re.compile(r"\b(19|20)\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b"), "[DATE]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[EMAIL]"),
    (re.compile(r"\(?\b\d{3}\)?[ .-]\d{3}[ .-]\d{4}\b"), "[PHONE]"),
    (re.compile(r"\b(member|mbr|id)[ #:]*[A-Z]{0,4}\d{6,}\b", re.I), "[MEMBER-ID]"),
    (re.compile(r"\b[A-Z]{2,4}\d{6,}\b"), "[ID]"),
    (re.compile(r"\bNPI[ #:]*\d{10}\b", re.I), "[NPI]"),
    (re.compile(r"\b\d{1,5} [A-Z][a-z]+ (St|Street|Ave|Avenue|Rd|Road|Blvd|Dr|Drive|Ln|Lane)\b"), "[ADDRESS]"),
]


def redact(text: str | None, names: list[str] | None = None) -> str:
    if not text:
        return text or ""
    out = text
    for n in sorted({n for n in (names or []) if n and len(n) > 2}, key=len, reverse=True):
        out = re.sub(re.escape(n), "[NAME]", out, flags=re.I)
        for part in n.split():
            if len(part) > 2:
                out = re.sub(rf"\b{re.escape(part)}\b", "[NAME]", out, flags=re.I)
    for rx, repl in PATTERNS:
        out = rx.sub(repl, out)
    return out


def case_names(session, case_id: int | None) -> list[str]:
    """Member + provider names from the latest AI review of the case (to redact them elsewhere)."""
    if not case_id:
        return []
    from app.repositories import cases as repo
    r = repo.latest_review(session, case_id)
    f = ((r.result or {}).get("fields") or {}) if r else {}
    return [f.get("member_name") or "", f.get("provider_name") or ""]


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
            red = redact(msg)
            if red != msg:
                record.msg, record.args = red, ()
        except Exception:
            pass
        return True


def install_log_filter() -> None:
    f = RedactingFilter()
    for name in ("", "uvicorn", "uvicorn.access", "uvicorn.error", "app"):
        lg = logging.getLogger(name)
        if not any(isinstance(x, RedactingFilter) for x in lg.filters):
            lg.addFilter(f)
        for h in lg.handlers:
            if not any(isinstance(x, RedactingFilter) for x in h.filters):
                h.addFilter(f)
