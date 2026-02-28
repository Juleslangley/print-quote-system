from __future__ import annotations

import hashlib
from pathlib import Path


_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_PO_HTML_PATH = _TEMPLATES_DIR / "purchase_order_premium.html.jinja"
_PO_CSS_PATH = _TEMPLATES_DIR / "purchase_order_premium.css"


def load_purchase_order_premium_template() -> tuple[str, str]:
    html = _PO_HTML_PATH.read_text(encoding="utf-8")
    css = _PO_CSS_PATH.read_text(encoding="utf-8")
    return html, css


def purchase_order_premium_version_id() -> str:
    html, css = load_purchase_order_premium_template()
    digest = hashlib.sha256(f"{html}\n/*css*/\n{css}".encode("utf-8")).hexdigest()
    return f"po-premium:{digest[:24]}"
