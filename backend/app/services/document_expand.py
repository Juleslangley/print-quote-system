"""Expand TipTap data-jinja-output blocks and fix corrupted line tables before Jinja render."""
from __future__ import annotations

import re

from jinja2 import Environment, BaseLoader, TemplateSyntaxError

from app.services.document_blocks import expand_block_placeholders, expand_legacy_data_jinja_output
from app.services.document_repair import run_repairs


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


# Match <table ... class="po-lines" ...>...</table> (works when wrapped by divs after expand)
_PO_LINES_PATTERN = r'<table[^>]*class=["\'][^"\']*\bpo-lines\b[^"\']*["\'][^>]*>[\s\S]*?</table>'


def _strip_stray_line_refs(text: str) -> str:
    """Replace {{ line.xxx }} outside a loop with — to avoid Jinja 'line' is undefined."""
    return re.sub(r'\{\{[^}]*line\.\w+[^}]*\}\}', "—", text)


def _strip_stray_if_endif_near_po_lines(html_content: str) -> str:
    """
    Remove orphaned {% if lines ... %} / {% endif %} fragments that are NOT inside
    the canonical po-lines table (within ~500 chars of the table boundary).
    TipTap sometimes splits the {% if %}...{% endif %} wrapper away from the table.
    """
    po_match = re.search(_PO_LINES_PATTERN, html_content, re.I)
    if not po_match:
        return html_content

    table_start = po_match.start()
    table_end = po_match.end()
    table_block = html_content[table_start:table_end]

    # Only act on the region OUTSIDE the canonical table
    before = html_content[:table_start]
    after = html_content[table_end:]

    _IF_LINES = re.compile(
        r'\{%\s*if\s+lines\s+(?:and\s+\(lines\|length\)\s*>\s*0\s*)?%\}', re.I
    )
    _ENDIF = re.compile(r'\{%\s*endif\s*%\}')
    _ELSE = re.compile(r'\{%\s*else\s*%\}')

    # Strip stray {% if lines ... %} within 500 chars before the table
    zone = before[-500:] if len(before) > 500 else before
    zone_prefix = before[:-500] if len(before) > 500 else ""
    zone = _IF_LINES.sub("", zone)
    zone = _ENDIF.sub("", zone)
    zone = _ELSE.sub("", zone)
    before = zone_prefix + zone

    # Strip stray {% endif %} within 500 chars after the table
    zone = after[:500]
    zone_rest = after[500:]
    zone = _ENDIF.sub("", zone)
    zone = _IF_LINES.sub("", zone)
    zone = _ELSE.sub("", zone)
    after = zone + zone_rest

    return before + table_block + after


def fix_corrupted_po_lines_block(html: str) -> str:
    """
    If {{ line. }} exists but no proper {% for line in lines %}...{% endfor %} wrapping it,
    replace the corrupted po-lines region with canonical table.
    """
    out = html
    for _ in range(10):  # bounded iteration
        prev = out
        out = _fix_corrupted_lines_table(out)
        if out == prev:
            break
    return out


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


def _balance_jinja_blocks(html_content: str) -> str:
    """
    Append missing {% endif %} and/or {% endfor %} when blocks are unbalanced.
    Fixes 'Unexpected end of template' from TipTap/editor stripping closing tags.
    """
    if not html_content:
        return html_content
    # Count block opens/closes (exclude {% elif %}, {% else %} which don't open new blocks)
    if_opens = len(re.findall(r"\{\%\s*if\s+", html_content))
    if_closes = len(re.findall(r"\{\%\s*endif\s*\%\}", html_content))
    for_opens = len(re.findall(r"\{\%\s*for\s+", html_content))
    for_closes = len(re.findall(r"\{\%\s*endfor\s*\%\}", html_content))
    missing_endfor = max(0, for_opens - for_closes)
    missing_endif = max(0, if_opens - if_closes)
    if missing_endfor or missing_endif:
        suffix = (" {% endfor %}" * missing_endfor) + (" {% endif %}" * missing_endif)
        return html_content + suffix
    return html_content


def expand_jinja_blocks(
    html_content: str, doc_type: str | None = "purchase_order", balance_blocks: bool = False
) -> str:
    """
    Replace <div data-jinja-block="po_lines"> and data-jinja-output with content.
    Fix corrupted line tables, enforce DOM order, deduplicate.
    Structural repairs (ampersands, stray refs, dedupe) run via document_repair.run_repairs.
    """
    if not html_content:
        return html_content

    # 0. Safety rewrite: old content may have data-jinja-output="true"; replace with ""
    html_content = _rewrite_jinja_output_true(html_content)

    # 1a. Expand data-jinja-block placeholders (po_lines, po_totals, barcode) from BLOCK_REGISTRY
    html_content = expand_block_placeholders(html_content)

    # 1b. Expand legacy data-jinja-output blocks (attr=""|"true" -> innerHTML; attr="..." -> value)
    html_content = expand_legacy_data_jinja_output(html_content)

    # 2. Fix corrupted line tables (iterate until stable) — TipTap unwrap logic
    while True:
        prev = html_content
        html_content = _fix_corrupted_lines_table(html_content)
        if html_content == prev:
            break

    # 3. Strip manual {% for line in lines %} loops outside canonical po-lines table
    html_content = _strip_manual_line_loops(html_content)

    # 4. Strip stray {% if lines %} / {% endif %} fragments near po-lines table
    html_content = _strip_stray_if_endif_near_po_lines(html_content)

    # 5. Enforce DOM order: header → po_lines → totals (reorder if corrupted)
    html_content = _enforce_po_dom_order(html_content)

    # 6. Structural repair layer: ampersands, stray line refs, dedupe tables
    html_content, repair_log = run_repairs(html_content, doc_type or "purchase_order")

    # 7. Balance unclosed blocks when rendering (not when validating)
    if balance_blocks:
        html_content = _balance_jinja_blocks(html_content)

    return html_content


def expand_jinja_blocks_with_log(
    html_content: str,
    doc_type: str | None = "purchase_order",
    balance_blocks: bool = False,
) -> tuple[str, list[str]]:
    """
    Same as expand_jinja_blocks but returns (html, repair_log) for debug tools.
    """
    if not html_content:
        return "", []

    html_content = _rewrite_jinja_output_true(html_content)
    html_content = expand_block_placeholders(html_content)
    html_content = expand_legacy_data_jinja_output(html_content)

    while True:
        prev = html_content
        html_content = _fix_corrupted_lines_table(html_content)
        if html_content == prev:
            break

    html_content = _strip_manual_line_loops(html_content)
    html_content = _strip_stray_if_endif_near_po_lines(html_content)
    html_content = _enforce_po_dom_order(html_content)
    html_content, repair_log = run_repairs(html_content, doc_type or "purchase_order")
    if balance_blocks:
        html_content = _balance_jinja_blocks(html_content)

    return html_content, repair_log


def repair_po_lines_html(html: str) -> str:
    """
    Full repair pass for purchase_order template HTML.
    Usable standalone (e.g. by Alembic migration) without expanding placeholders.
    """
    if not html:
        return html
    html = _rewrite_jinja_output_true(html)
    html = expand_block_placeholders(html)
    html = expand_legacy_data_jinja_output(html)
    while True:
        prev = html
        html = _fix_corrupted_lines_table(html)
        if html == prev:
            break
    html = _strip_manual_line_loops(html)
    html = _strip_stray_if_endif_near_po_lines(html)
    html = _enforce_po_dom_order(html)
    html, _ = run_repairs(html, "purchase_order")
    html = _balance_jinja_blocks(html)
    return html


def validate_template_jinja(
    template_html: str,
    template_css: str | None = None,
    content: str = "",
    doc_type: str | None = "purchase_order",
) -> tuple[bool, str]:
    """
    Expand template, parse with Jinja; return (True, "") if valid, else (False, error_message).
    On TemplateSyntaxError returns helpful message with line number and nearby context.
    """
    body = template_html or content
    if not body.strip():
        return True, ""
    try:
        expanded = expand_jinja_blocks(body, doc_type=doc_type or "purchase_order")
        doc = f"<!doctype html><html><head></head><body>{expanded}</body></html>"
        env = Environment(loader=BaseLoader())
        env.parse(doc)
        return True, ""
    except TemplateSyntaxError as e:
        return False, _format_template_syntax_error(
            f"<!doctype html><html><head></head><body>{expanded}</body></html>", e
        )


def _format_template_syntax_error(template_source: str, e: TemplateSyntaxError) -> str:
    """Build helpful error message with line number and nearby context."""
    lineno = getattr(e, "lineno", None) or 0
    msg = str(e).strip()
    if "expected 'elif' or 'else' or 'endif'" in msg or "innermost block is" in msg:
        prefix = "Jinja syntax error (unbalanced block)"
    else:
        prefix = "Jinja syntax error"
    if lineno and lineno > 0:
        lines = template_source.splitlines()
        snippet_lines = []
        for i in range(max(0, lineno - 2), min(len(lines), lineno + 1)):
            marker = ">>> " if i == lineno - 1 else "    "
            snippet_lines.append(f"{marker}{i + 1}: {lines[i]}")
        ctx = "\n".join(snippet_lines) if snippet_lines else ""
        return f"{prefix} near line {lineno}: {msg}\n{ctx}" if ctx else f"{prefix} (line {lineno}): {msg}"
    return f"{prefix}: {msg}"
