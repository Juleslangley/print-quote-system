"""Expand TipTap data-jinja-output blocks and fix corrupted line tables before Jinja render."""
from __future__ import annotations

import html
import re

from jinja2 import Environment, BaseLoader, TemplateSyntaxError

# Replace bare & in plain HTML text with &amp; (e.g. "Smith & Sons")
_PLAIN_AMP = re.compile(r"&(?!(?:amp|lt|gt|quot|#\d+);)")


def _fix_plain_ampersands(text: str) -> str:
    """Replace bare & in plain text with &amp; (skip Jinja blocks)."""
    parts = re.split(r"(\{\{.*?\}\}|\{%.*?%\})", text, flags=re.DOTALL)
    for i in range(0, len(parts), 2):
        parts[i] = _PLAIN_AMP.sub("&amp;", parts[i])
    return "".join(parts)


# Fix & and && inside Jinja blocks (Jinja uses 'and' not & or &&)
def _fix_jinja_ampersands(text: str) -> str:
    def fix_block(inner: str) -> str:
        inner = html.unescape(inner)
        inner = inner.replace("&&", "and")
        inner = re.sub(r"\s+&\s+", " and ", inner)
        return inner

    def fix_expr(m: re.Match) -> str:
        inner = m.group(1)
        if "&" not in inner and "&" not in html.unescape(inner):
            return m.group(0)
        return "{{" + fix_block(inner) + "}}"

    def fix_tag(m: re.Match) -> str:
        inner = m.group(1)
        if "&" not in inner and "&" not in html.unescape(inner):
            return m.group(0)
        return "{%" + fix_block(inner) + "%}"

    text = re.sub(r"\{\{(.*?)\}\}", fix_expr, text, flags=re.DOTALL)
    text = re.sub(r"\{%(.*?)%\}", fix_tag, text, flags=re.DOTALL)
    return text




# Canonical PO lines table - single self-contained block (po-lines matches migration 024 CSS)
_LINES_TABLE_JINJA = """<table class="po-lines"><thead><tr><th>Description</th><th>Supplier code</th><th class="right">Qty</th><th>UOM</th><th class="right">Unit cost</th><th class="right">Line total</th></tr></thead><tbody>{% if lines and (lines|length) > 0 %}
{% for line in lines %}
<tr>
<td>{{ line.description or '—' }}</td>
<td>{{ line.supplier_product_code or '—' }}</td>
<td class="right">{{ '%.2f'|format(line.qty or 0) }}</td>
<td>{{ line.uom or '—' }}</td>
<td class="right">£{{ '%.2f'|format(line.unit_cost_gbp or 0) }}</td>
<td class="right">£{{ '%.2f'|format(line.line_total_gbp or 0) }}</td>
</tr>
{% endfor %}
{% else %}
<tr><td colspan="6" class="center">No lines</td></tr>
{% endif %}
</tbody></table>"""


def _strip_stray_line_refs(text: str) -> str:
    """Replace {{ line.xxx }} outside a loop with — to avoid Jinja 'line' is undefined."""
    return re.sub(r'\{\{[^}]*line\.\w+[^}]*\}\}', "—", text)


def _fix_corrupted_lines_table(html_content: str) -> str:
    """
    Fix TipTap-mangled table where {% for line in lines %}{% endfor %} is empty
    and {{ line.* }} appear outside the loop. Replace the entire mangled region.
    """
    if "{{ line." not in html_content:
        return html_content

    # Corrupted: {{ line.xxx }} exists. Check if it's inside a proper loop.
    # Proper: {% for line in lines %}...{{ line.xxx }}...{% endfor %}
    # Corrupted: {% for line in lines %} {% endfor %} ... {{ line.xxx }} (empty loop, line refs outside)
    loop_match = re.search(
        r'\{%\s*for\s+line\s+in\s+lines\s*%\}([\s\S]*?)\{%\s*endfor\s*%\}',
        html_content,
    )
    if not loop_match:
        # No loop at all - strip stray {{ line.xxx }} to avoid undefined
        return _strip_stray_line_refs(html_content)

    loop_body = loop_match.group(1)
    if "{{ line." in loop_body:
        return html_content  # Proper loop with <tr> rows inside, no fix needed

    # Corrupted: empty loop body (TipTap stripped the <tr> rows)
    # Fix regardless of where {{ line. }} ended up - empty loop always produces broken output

    # Replace: find <table> before this block, and </table> after
    table_start = html_content.rfind("<table", 0, loop_match.start() + 1)
    table_end = html_content.find("</table>", loop_match.start())

    # Fallback: if no table wrapper, replace from {% if lines %} to {% endif %}
    if table_start < 0:
        if_block = re.search(
            r'\{%\s*if\s+lines\s+and\s+\(lines\|length\)\s*>\s*0\s*%\}[\s\S]*?\{%\s*endif\s*%\}',
            html_content,
        )
        if if_block:
            tail = html_content[if_block.end():]
            tail = _strip_stray_line_refs(tail)
            return html_content[: if_block.start()] + _LINES_TABLE_JINJA + tail
        table_start = loop_match.start()
    if table_end >= 0:
        tail = html_content[table_end + len("</table>"):]
        tail = _strip_stray_line_refs(tail)
        return html_content[:table_start] + _LINES_TABLE_JINJA + tail

    # No </table> - TipTap may have split into divs/paras. Find next table (totals) to keep.
    next_table = html_content.find("<table", loop_match.start() + 1)
    if next_table >= 0:
        tail = _strip_stray_line_refs(html_content[next_table:])
        return html_content[:table_start] + _LINES_TABLE_JINJA + tail

    # Fallback: find totals section (class="totals") to preserve
    totals_pos = html_content.find('class="totals"', loop_match.end())
    if totals_pos < 0:
        totals_pos = html_content.find("class='totals'", loop_match.end())
    if totals_pos >= 0:
        tbl = html_content.rfind("<table", loop_match.end(), totals_pos + 1)
        if tbl >= 0:
            tail = _strip_stray_line_refs(html_content[tbl:])
            return html_content[:table_start] + _LINES_TABLE_JINJA + tail

    # Last resort: drop corrupted region, strip stray {{ line.* }} from tail
    tail = html_content[loop_match.end():]
    tail = _strip_stray_line_refs(tail)
    return html_content[:table_start] + _LINES_TABLE_JINJA + tail


def _rewrite_jinja_output_true(html_content: str) -> str:
    """Replace data-jinja-output=\"true\" with data-jinja-output=\"\" so we never emit literal 'true'."""
    return re.sub(r'data-jinja-output="true"', 'data-jinja-output=""', html_content, flags=re.IGNORECASE)


# Match <table ... class="po-lines" ...>...</table> (works when wrapped by divs after expand)
_PO_LINES_PATTERN = r'<table[^>]*class=["\'][^"\']*\bpo-lines\b[^"\']*["\'][^>]*>[\s\S]*?</table>'


def _remove_orphan_no_lines_fragments(html_content: str, first_table_end: int) -> str:
    """
    Remove orphan fallback fragments containing "No lines" that appear AFTER the
    canonical po-lines table. These are static duplicates that cause double rendering.
    Only removes blocks that do NOT contain the Jinja loop ({% for line in lines %}).
    """
    tail = html_content[first_table_end:]
    if "No lines" not in tail:
        return html_content
    # Match <table>...</table> blocks that contain "No lines" but no Jinja loop
    def remove_orphan(m: re.Match) -> str:
        block = m.group(0)
        if "{% for line" in block or "{% if lines" in block:
            return block  # Keep: canonical table has Jinja
        if "No lines" in block:
            return ""  # Remove: static fallback fragment
        return block

    pattern = re.compile(r"<table[^>]*>[\s\S]*?</table>", re.IGNORECASE)
    cleaned_tail = pattern.sub(remove_orphan, tail)
    return html_content[:first_table_end] + cleaned_tail


def deduplicate_po_lines_tables(html_content: str) -> str:
    """
    Keep only the first po-lines table; remove duplicates and orphan fallback fragments.
    Prevents double rendering (table + "No lines" again) when template has both
    canonical table and static fallback.
    Run AFTER expand_jinja_blocks data-jinja-output expansion and any TipTap unwrap logic.
    """
    if not html_content or "po-lines" not in html_content:
        return html_content
    tables = re.findall(_PO_LINES_PATTERN, html_content, flags=re.I)
    if len(tables) > 1:
        first = tables[0]
        html_content = re.sub(_PO_LINES_PATTERN, "", html_content, flags=re.I)
        html_content = first + html_content
    # Remove orphan "No lines" fragments after the first table
    first_match = re.search(_PO_LINES_PATTERN, html_content, flags=re.I)
    if first_match:
        html_content = _remove_orphan_no_lines_fragments(html_content, first_match.end())
    return html_content


def _expand_data_jinja_block(html_content: str) -> str:
    """Expand <div data-jinja-block="po_lines"> to canonical table. Ensures single block."""
    return re.sub(
        r'<div[^>]*\sdata-jinja-block=["\']po_lines["\'][^>]*>[\s\S]*?</div>',
        _LINES_TABLE_JINJA,
        html_content,
        flags=re.IGNORECASE,
    )


def _strip_manual_line_loops(html_content: str) -> str:
    """Remove manual {% for line in lines %}...{% endfor %} blocks outside the canonical po-lines table."""
    # Canonical: loop body has <tr> and {{ line. }} (proper table rows). Keep it.
    # Orphan/corrupt: loop body empty or lacks <tr>. Remove it.
    def remove_if_orphan(m: re.Match) -> str:
        block = m.group(0)
        loop_body = block
        if "{% endfor %}" in block:
            loop_body = block.split("{% endfor %}")[0].split("{% for line in lines %}")[-1]
        if "{{ line." in loop_body and "<tr>" in loop_body:
            return block  # Keep: canonical table row loop
        return ""  # Remove: empty or corrupt loop

    pattern = r'\{%\s*for\s+line\s+in\s+lines\s*%\}[\s\S]*?\{%\s*endfor\s*%\}'
    return re.sub(pattern, remove_if_orphan, html_content)


_PO_TOTALS_WRAP_PATTERN = (
    r'<div[^>]*class=["\'][^"\']*po-totals-wrap[^"\']*["\'][^>]*>[\s\S]*?<table[^>]*class=["\'][^"\']*po-totals[^"\']*["\'][^>]*>[\s\S]*?</table>[\s\S]*?</div>'
)
_PO_TOTALS_TABLE_PATTERN = r'<table[^>]*class=["\'][^"\']*po-totals[^"\']*["\'][^>]*>[\s\S]*?</table>'


def _enforce_po_dom_order(html_content: str) -> str:
    """Enforce DOM order: header → po_lines table → totals. Reorder if corrupted."""
    if "po-lines" not in html_content or "po-totals" not in html_content:
        return html_content
    po_match = re.search(_PO_LINES_PATTERN, html_content, re.I)
    totals_match = re.search(_PO_TOTALS_WRAP_PATTERN, html_content, re.I)
    if not totals_match:
        totals_match = re.search(_PO_TOTALS_TABLE_PATTERN, html_content, re.I)
    if not po_match or not totals_match:
        return html_content
    po_start, po_end = po_match.start(), po_match.end()
    tot_start, tot_end = totals_match.start(), totals_match.end()
    # Correct order: po before totals
    if po_start < tot_start:
        return html_content
    # Wrong: totals before po_lines — reorder
    before_totals = html_content[:tot_start]
    totals_block = html_content[tot_start:tot_end]
    between = html_content[tot_end:po_start]
    po_block = html_content[po_start:po_end]
    after_po = html_content[po_end:]
    return before_totals + po_block + between + totals_block + after_po


def expand_jinja_blocks(html_content: str) -> str:
    """
    Replace <div data-jinja-block="po_lines"> and data-jinja-output with content.
    Fix corrupted line tables, enforce DOM order, deduplicate.
    """
    if not html_content:
        return html_content

    # 0. Safety rewrite: old content may have data-jinja-output="true"; replace with ""
    html_content = _rewrite_jinja_output_true(html_content)

    # 1a. Expand data-jinja-block="po_lines" placeholders to canonical table
    html_content = _expand_data_jinja_block(html_content)

    # 1b. Expand data-jinja-output blocks: replace div with its content before render.
    # attr missing/""/"true" -> use innerHTML (never emit literal "true")
    # attr = "JINJA_STRING" -> use attribute value (legacy)
    if "data-jinja-output" in html_content:
        def replacer(m: re.Match) -> str:
            attr_val = m.group(1) or ""
            inner = m.group(2)
            if attr_val.strip() == "" or attr_val.strip().lower() == "true":
                return inner
            return html.unescape(attr_val)

        pattern = r'<div[^>]*\sdata-jinja-output="([^"]*)"[^>]*>([\s\S]*?)</div>'
        html_content = re.sub(pattern, replacer, html_content)

    # 2. Fix & and && inside Jinja blocks (after expand, before render)
    html_content = _fix_jinja_ampersands(html_content)

    # 3. Fix bare & in plain text (e.g. company names)
    html_content = _fix_plain_ampersands(html_content)

    # 4. Fix corrupted line tables (iterate until stable) — TipTap unwrap logic
    while True:
        prev = html_content
        html_content = _fix_corrupted_lines_table(html_content)
        if html_content == prev:
            break

    # 5. Strip manual {% for line in lines %} loops outside canonical po-lines table
    html_content = _strip_manual_line_loops(html_content)

    # 6. Deduplicate po-lines tables — run AFTER expand, sanitizer, TipTap unwrap
    html_content = deduplicate_po_lines_tables(html_content)

    # 7. Enforce DOM order: header → po_lines → totals (reorder if corrupted)
    html_content = _enforce_po_dom_order(html_content)

    return html_content


def validate_template_jinja(template_html: str, template_css: str | None = None, content: str = "") -> tuple[bool, str]:
    """
    Parse template with Jinja; return (True, "") if valid, else (False, error_message).
    Uses the same expansion as render. Checks for unbalanced blocks (e.g. missing endif).
    """
    body = template_html or content
    if not body.strip():
        return True, ""
    try:
        expanded = expand_jinja_blocks(body)
        doc = f"<!doctype html><html><head></head><body>{expanded}</body></html>"
        env = Environment(loader=BaseLoader())
        env.parse(doc)
        return True, ""
    except TemplateSyntaxError as e:
        msg = str(e)
        if "expected 'elif' or 'else' or 'endif'" in msg or "innermost block is" in msg:
            return False, f"Jinja syntax error: unbalanced block — {msg}"
        return False, f"Jinja syntax error: {msg}"
