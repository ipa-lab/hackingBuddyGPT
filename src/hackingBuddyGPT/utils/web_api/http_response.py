"""Shared HTTP status-line parsing for the web-API prototypes.

The response analyzer and the OpenAPI specification handler both need the status code (and
message) out of a raw HTTP response. They used to carry an identical status-line regex each;
this is the single source for it.

Note: ``ResponseHandler.parse_http_status_line`` intentionally keeps its own, stricter parse
(exact 3-digit code, raises on malformed input, plus domain special-cases) and is not routed
through here.
"""
import re
from typing import Optional, Tuple

_STATUS_LINE_RE = re.compile(r"^HTTP/\d\.\d\s+(\d+)\s+(.*)", re.MULTILINE)


def extract_status_code_and_message(text) -> Tuple[Optional[str], Optional[str]]:
    """Return ``(status_code, status_message)`` from an HTTP response, or ``(None, None)``.

    ``status_code`` is the code as a string; ``status_message`` is stripped of surrounding
    whitespace. Non-string input is coerced with ``str()`` first.
    """
    if not isinstance(text, str):
        text = str(text)
    match = _STATUS_LINE_RE.search(text)
    if match:
        return match.group(1), match.group(2).strip()
    return None, None
