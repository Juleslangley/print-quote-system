import { Node } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";

/** Canonical PO lines table HTML/Jinja payload — immutable, never split by ProseMirror. */
export const PO_LINES_TEMPLATE_HTML = `<table class="po-lines">
<thead>
<tr>
<th>Description</th>
<th>Supplier code</th>
<th class="right">Qty</th>
<th>UOM</th>
<th class="right">Unit cost</th>
<th class="right">Line total</th>
</tr>
</thead>
<tbody>
{% if lines and (lines|length) > 0 %}
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
</tbody>
</table>`;

function asElement(dom: unknown): Element | null {
  try {
    if (!dom || (dom as globalThis.Node).nodeType !== 1) return null;
    const el = dom as Element;
    return typeof el.getAttribute === "function" ? el : null;
  } catch {
    return null;
  }
}

/**
 * Atomic PO Line Items block — truly locked, non-editable.
 * Stores real HTML/Jinja in templateHtml; serializes to data-template-block div for zero chance of ProseMirror splitting {% %} tags.
 */
export const PoLinesBlock = Node.create({
  name: "poLinesBlock",
  group: "block",
  atom: true,
  selectable: true,
  draggable: false,
  defining: true,

  addAttributes() {
    return {
      templateHtml: {
        default: PO_LINES_TEMPLATE_HTML,
        parseHTML: (el) => {
          const elem = asElement(el);
          if (!elem) return PO_LINES_TEMPLATE_HTML;
          const inner = elem.innerHTML?.trim();
          return inner ? inner : PO_LINES_TEMPLATE_HTML;
        },
        renderHTML: () => ({}),
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'div[data-template-block="po-lines"]',
        priority: 80,
        getAttrs: (dom) => {
          const el = asElement(dom);
          if (!el) return false;
          const inner = el.innerHTML?.trim();
          return { templateHtml: inner || PO_LINES_TEMPLATE_HTML };
        },
      },
      {
        tag: 'div[data-jinja-block="po_lines"]',
        priority: 70,
        getAttrs: () => ({ templateHtml: PO_LINES_TEMPLATE_HTML }),
      },
      {
        tag: "div.po-lines-block",
        priority: 65,
        getAttrs: () => ({ templateHtml: PO_LINES_TEMPLATE_HTML }),
      },
    ];
  },

  renderHTML({ node }) {
    const html = node.attrs.templateHtml ?? PO_LINES_TEMPLATE_HTML;
    if (typeof document !== "undefined") {
      const div = document.createElement("div");
      div.setAttribute("data-template-block", "po-lines");
      div.setAttribute("data-jinja-output", "true");
      div.innerHTML = html;
      return div;
    }
    return [
      "div",
      {
        "data-template-block": "po-lines",
        "data-jinja-output": "true",
      },
      0,
    ];
  },

  addNodeView() {
    return () => {
      const dom = document.createElement("div");
      dom.setAttribute("contenteditable", "false");
      dom.className = "locked-block";
      dom.setAttribute("data-node-view-wrapper", "");

      const title = document.createElement("div");
      title.className = "locked-title";
      title.textContent = "PO Line Items Table (locked)";

      dom.appendChild(title);

      return {
        dom,
        ignoreMutation: () => true,
        stopEvent: () => true,
      };
    };
  },

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey("poLinesBlockPreventDelete"),
        props: {
          handleKeyDown: (view, event) => {
            if (event.key !== "Backspace" && event.key !== "Delete") return false;
            const { state } = view;
            const $pos = state.selection.$anchor;
            for (let d = $pos.depth; d > 0; d--) {
              if ($pos.node(d).type.name === "poLinesBlock") {
                event.preventDefault();
                return true;
              }
            }
            return false;
          },
        },
      }),
    ];
  },
});
