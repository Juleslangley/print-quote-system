from app.services.jinja_normalize import normalize_jinja_operators_in_tokens


def test_normalize_if_gt_inside_jinja_tag():
    html = "{% if (lines|length) &gt; 0 %}<p>ok</p>{% endif %}"
    out = normalize_jinja_operators_in_tokens(html)
    assert "{% if (lines|length) > 0 %}" in out
    assert "&gt;" not in out


def test_normalize_lt_inside_jinja_expr():
    html = "{{ 1 &lt; 2 }}"
    out = normalize_jinja_operators_in_tokens(html)
    assert out == "{{ 1 < 2 }}"


def test_outside_html_entities_unchanged():
    html = "<p>HTML text &gt; outside</p>"
    out = normalize_jinja_operators_in_tokens(html)
    assert out == html


def test_multiline_jinja_if_block_normalized():
    html = "{% if\n  (lines|length) &gt; 0\n%}\n{{ 1 &lt; 2 }}\n{% endif %}"
    out = normalize_jinja_operators_in_tokens(html)
    assert "&gt;" not in out
    assert "&lt;" not in out
    assert "> 0" in out
    assert "{{ 1 < 2 }}" in out


def test_normalize_idempotent():
    html = "{% if x &amp;gt; 0 and y &lt; 10 %}{{ a &gt; b }}{% endif %}"
    once = normalize_jinja_operators_in_tokens(html)
    twice = normalize_jinja_operators_in_tokens(once)
    assert once == twice
