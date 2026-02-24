"""
Structural repair layer for document templates.
Runs after placeholder expansion, before validate/render.
Ensures no duplicate tables, no stray line refs, ampersands normalized.
"""
from __future__ import annotations

import html as html_module
import re
from typing import Tuple

# Match <table ... class="NAME" ...>...</table>
def _table_pattern(class_name: str) -> str:
    safe = re.escape(class_name)
    return rf'<table[^>]*class=["\'][^"\']*\b{safe}\b[^"\']*["\'][^>]*>[\s\S]*?</table>'


def deduplicate_po_lines_tables(html: str) -> str:
    """Keep only first <table class="po-lines">...</table>; remove later duplicates."""
    result, _ = dedupe_tables(html, "po-lines")
    return result


def dedupe_tables(html: str, class_name: str = "po-lines") -> Tuple[str, list[str]]:
    """
    Keep first table with given class; remove duplicates and orphan fragments.
    For po-lines: also removes orphan "No lines" tables after the first.
    Returns (repaired_html, repair_log).
    """
    log: list[str] = []
    if not html or class_name not in html.lower():
        return html, log

    pattern = _table_pattern(class_name)
    tables = list(re.finditer(pattern, html, re.I))
    if len(tables) <= 1:
        # Still remove orphan "No lines" fragments after first table (po-lines only)
        if class_name == "po-lines" and tables:
            first_end = tables[0].end()
            tail = html[first_end:]
            if "No lines" in tail:
                def remove_orphan(m: re.Match) -> str:
                    block = m.group(0)
                    if "{% for line" in block or "{% if lines" in block:
                        return block
                    if "No lines" in block:
                        return ""
                    return block
                orphan_pat = re.compile(r"<table[^>]*>[\s\S]*?</table>", re.I)
                cleaned = orphan_pat.sub(remove_orphan, tail)
                if cleaned != tail:
                    html = html[:first_end] + cleaned
                    log.append("removed_orphan_no_lines_fragments")
        return html, log

    first = tables[0].group(0)
    html = re.sub(pattern, "", html, flags=re.I)
    html = first + html
    log.append(f"deduped_{class_name}_tables: kept first of {len(tables)}")

    # Orphan "No lines" cleanup for po-lines
    if class_name == "po-lines":
        first_match = re.search(pattern, html, re.I)
        if first_match:
            tail = html[first_match.end():]
            if "No lines" in tail:
                def remove_orphan(m: re.Match) -> str:
                    block = m.group(0)
                    if "{% for line" in block or "{% if lines" in block:
                        return block
                    if "No lines" in block:
                        return ""
                    return block
                orphan_pat = re.compile(r"<table[^>]*>[\s\S]*?</table>", re.I)
                cleaned = orphan_pat.sub(remove_orphan, tail)
                html = html[:first_match.end()] + cleaned
                log.append("removed_orphan_no_lines_fragments")

    return html, log


def strip_stray_line_refs(html: str) -> Tuple[str, list[str]]:
    """
    Replace {{ line.xxx }} outside {% for line in lines %}...{% endfor %} with "—".
    Prevents "line is undefined" Jinja errors. Only touches refs outside the canonical
    po-lines table (which contains the loop).
    """
    log: list[str] = []
    if "{{ line." not in html:
        return html, log

    pattern = _table_pattern("po-lines")
    table_match = re.search(pattern, html, re.I)
    if not table_match:
        # No po-lines table; strip all {{ line.xxx }}
        def repl(_: re.Match) -> str:
            return "—"
        out = re.sub(r'\{\{[^}]*line\.\w+[^}]*\}\}', repl, html)
        if out != html:
            log.append("strip_stray_line_refs: no po-lines table, replaced all")
        return out, log

    before = html[: table_match.start()]
    table_block = html[table_match.start() : table_match.end()]
    after = html[table_match.end() :]

    def repl(_: re.Match) -> str:
        return "—"

    before_fixed = re.sub(r'\{\{[^}]*line\.\w+[^}]*\}\}', repl, before)
    after_fixed = re.sub(r'\{\{[^}]*line\.\w+[^}]*\}\}', repl, after)
    out = before_fixed + table_block + after_fixed
    if out != html:
        log.append("strip_stray_line_refs: replaced refs outside po-lines table")
    return out, log


def normalize_ampersands(html: str) -> Tuple[str, list[str]]:
    """
    Inside Jinja: replace & and && with 'and'.
    Outside Jinja: escape bare & -> &amp; (keep existing entities like &amp; &lt;).
    """
    log: list[str] = []
    _PLAIN_AMP = re.compile(r"&(?!(?:amp|lt|gt|quot|#\d+);)")

    # 1. Inside Jinja blocks: &/&& -> and
    def fix_block(inner: str) -> str:
        inner = html_module.unescape(inner)
        inner = inner.replace("&&", "and")
        inner = re.sub(r"\s+&\s+", " and ", inner)
        return inner

    def fix_expr(m: re.Match) -> str:
        inner = m.group(1)
        if "&" not in inner and "&" not in html_module.unescape(inner):
            return m.group(0)
        return "{{" + fix_block(inner) + "}}"

    def fix_tag(m: re.Match) -> str:
        inner = m.group(1)
        if "&" not in inner and "&" not in html_module.unescape(inner):
            return m.group(0)
        return "{%" + fix_block(inner) + "%}"

    prev = html
    html = re.sub(r"\{\{(.*?)\}\}", fix_expr, html, flags=re.DOTALL)
    html = re.sub(r"\{%(.*?)%\}", fix_tag, html, flags=re.DOTALL)
    if html != prev:
        log.append("normalize_ampersands: fixed Jinja &/&&")

    # 2. Outside Jinja: bare & -> &amp;
    parts = re.split(r"(\{\{.*?\}\}|\{%.*?%\})", html, flags=re.DOTALL)
    for i in range(0, len(parts), 2):
        parts[i] = _PLAIN_AMP.sub("&amp;", parts[i])
    out = "".join(parts)
    if out != html:
        log.append("normalize_ampersands: escaped bare & outside Jinja")
    return out, log


def ensure_single_placeholder(html: str, block_name: str) -> Tuple[str, list[str]]:
    """
    Keep first div[data-jinja-block="block_name"]; remove duplicates.
    Returns (repaired_html, repair_log).
    """
    log: list[str] = []
    pattern = rf'<div[^>]*\sdata-jinja-block=["\']{re.escape(block_name)}["\'][^>]*>[\s\S]*?</div>'
    matches = list(re.finditer(pattern, html, re.IGNORECASE))
    if len(matches) <= 1:
        return html, log

    count = [0]
    def replacer(m: re.Match) -> str:
        count[0] += 1
        return m.group(0) if count[0] == 1 else ""

    out = re.sub(pattern, replacer, html, flags=re.IGNORECASE)
    log.append(f"ensure_single_placeholder: {block_name} kept first of {len(matches)}")
    return out, log


def run_repairs(
    html: str,
    doc_type: str | None = "purchase_order",
) -> Tuple[str, list[str]]:
    """
    Run full structural repair pipeline. Call after expanding placeholders.
    ensure_single_placeholder is for SAVE path (pre-expansion); run_repairs is for RENDER path (post-expansion).
    Returns (repaired_html, repair_log).
    """
    log: list[str] = []

    # 1. Normalize ampersands
    html, sublog = normalize_ampersands(html)
    log.extend(sublog)

    # 2. Strip stray {{ line.xxx }} outside loops
    html, sublog = strip_stray_line_refs(html)
    log.extend(sublog)

    # 3. Dedupe po-lines / po-totals (purchase_order only)
    if doc_type == "purchase_order":
        html, sublog = dedupe_tables(html, "po-lines")
        log.extend(sublog)
        html, sublog = dedupe_tables(html, "po-totals")
        log.extend(sublog)

    return html, log
