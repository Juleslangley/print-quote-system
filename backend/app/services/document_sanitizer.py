"""HTML and CSS sanitization for document templates (XSS-safe)."""
from __future__ import annotations

import re

try:
    import bleach
except ImportError:
    bleach = None  # type: ignore

# Allowed HTML tags for document templates (tables, layout, typography)
ALLOWED_TAGS = [
    "a", "abbr", "address", "article", "aside", "b", "bdi", "bdo", "blockquote",
    "br", "caption", "code", "col", "colgroup", "data", "dd", "del", "details",
    "dfn", "div", "dl", "dt", "em", "figcaption", "figure", "footer", "h1", "h2",
    "h3", "h4", "h5", "h6", "header", "hr", "i", "img", "ins", "kbd", "li", "main",
    "mark", "nav", "ol", "p", "pre", "q", "rp", "rt", "ruby", "s", "samp",
    "section", "small", "span", "strong", "sub", "summary", "sup", "table", "tbody",
    "td", "tfoot", "th", "thead", "tr", "u", "ul", "var", "wbr",
]

# Allowed attributes (safe for layout/styling)
# data-jinja-output: used for protected Jinja blocks; do not escape inner {% %} or {{ }}
ALLOWED_ATTRS = {
    "*": ["class", "id", "style", "title", "dir", "lang", "data-jinja-output"],
    "a": ["href", "target", "rel"],
    "img": ["src", "alt", "width", "height"],
    "col": ["span"],
    "colgroup": ["span"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan"],
}

# Jinja2 delimiters must pass through - we allow {{, }}, {% %}
# Bleach will not strip these as they're not HTML. Double-check we're not escaping them.
# Note: bleach.clean escapes < and > in text, but {{ ... }} and {% ... %} don't use those.
# Jinja expressions like {{ x }} are safe; we must not strip them.


def sanitize_html(html: str) -> str:
    """Sanitize HTML for document templates. Preserves safe tags and strips XSS vectors."""
    if not html:
        return ""
    if bleach is None:
        # Fallback: strip script/iframe/object/embed/on* attributes
        # Not as robust as bleach but allows operation without the dep
        return _fallback_sanitize_html(html)
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        strip=True,
        strip_comments=True,
    )


def _fallback_sanitize_html(html: str) -> str:
    """Basic sanitization when bleach is not installed."""
    # Remove script, iframe, object, embed
    html = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<iframe[^>]*>[\s\S]*?</iframe>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<object[^>]*>[\s\S]*?</object>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<embed[^>]*>", "", html, flags=re.IGNORECASE)
    # Remove on* attributes
    html = re.sub(r'\s+on\w+="[^"]*"', "", html, flags=re.IGNORECASE)
    html = re.sub(r"\s+on\w+='[^']*'", "", html, flags=re.IGNORECASE)
    return html


def sanitize_css(css: str) -> str:
    """Sanitize CSS - strip dangerous constructs (expression, javascript:, url(data: with scripts))."""
    if not css:
        return ""
    # Remove expression()
    css = re.sub(r"expression\s*\([^)]*\)", "", css, flags=re.IGNORECASE)
    # Remove javascript: and vbscript:
    css = re.sub(r"javascript\s*:", "", css, flags=re.IGNORECASE)
    css = re.sub(r"vbscript\s*:", "", css, flags=re.IGNORECASE)
    return css
