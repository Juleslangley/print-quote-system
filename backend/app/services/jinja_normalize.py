import re


_JINJA_TOKEN_RE = re.compile(r"(\{%\s*[\s\S]*?%\}|\{\{[\s\S]*?\}\})")


def normalize_jinja_operators_in_tokens(template_html: str) -> str:
    """
    Normalize HTML-encoded comparison operators inside Jinja tokens only.

    - {% ... %} and {{ ... }} are scanned non-greedily.
    - Outside those tokens, HTML remains untouched.
    """
    source = template_html or ""

    def _normalize_token(match: re.Match) -> str:
        token = match.group(0)
        # Defensive: handle double-encoded operator entities first.
        token = token.replace("&amp;gt;", "&gt;").replace("&amp;lt;", "&lt;")
        # Then decode operator entities inside Jinja token text.
        token = token.replace("&gt;", ">").replace("&lt;", "<")
        return token

    return _JINJA_TOKEN_RE.sub(_normalize_token, source)
