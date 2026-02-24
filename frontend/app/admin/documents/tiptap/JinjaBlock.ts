import { Node } from "@tiptap/core";

export const JinjaBlock = Node.create({
  name: "jinjaBlock",
  group: "block",
  atom: true,
  selectable: true,
  draggable: true,

  addAttributes() {
    return {
      payload: {
        default: "",
        parseHTML: (el) => {
          const elem = el as HTMLElement;
          const attr = elem.getAttribute("data-jinja-output");
          if (attr != null && attr.trim().length > 0) {
            return attr;
          }
          return elem.innerHTML?.trim() || "";
        },
        renderHTML: (attrs) => (attrs.payload ? { "data-jinja-output": attrs.payload } : {}),
      },
      block: {
        default: null as string | null,
        parseHTML: (el) => (el as HTMLElement).getAttribute("data-jinja-block") || null,
        renderHTML: (attrs) => (attrs.block ? { "data-jinja-block": attrs.block } : {}),
      },
      label: {
        default: "Jinja Block",
        parseHTML: (el) => (el as HTMLElement).getAttribute("data-label") || "Jinja Block",
        renderHTML: (attrs) => (attrs.label ? { "data-label": attrs.label } : {}),
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: "div[data-jinja-block]",
        priority: 65,
        getAttrs: (dom) => {
          const el = dom as HTMLElement;
          const block = el.getAttribute("data-jinja-block");
          return block ? { block, payload: "", label: block === "po_lines" ? "PO Line Items Table" : "Jinja Block" } : false;
        },
      },
      {
        tag: "div[data-jinja-output]",
        priority: 60,
        getAttrs: (dom) => {
          const el = dom as HTMLElement;
          const attr = el.getAttribute("data-jinja-output");
          const payload = attr != null && attr.trim().length > 0 ? attr : el.innerHTML?.trim() || "";
          const label = el.getAttribute("data-label") || "Jinja Block";
          return { payload, label };
        },
      },
      {
        tag: "table.po-lines",
        priority: 55,
        getAttrs: (dom) => {
          const el = dom as HTMLElement;
          return { payload: el.outerHTML, label: "PO Line Items Table" };
        },
      },
    ];
  },

  renderHTML({ node, HTMLAttributes }) {
    const attrs: Record<string, string> = {
      ...HTMLAttributes,
      "data-label": node.attrs.label || "Jinja Block",
      contenteditable: "false",
    };
    if (node.attrs.block) {
      attrs["data-jinja-block"] = node.attrs.block;
    } else if (node.attrs.payload) {
      attrs["data-jinja-output"] = node.attrs.payload;
    }
    return ["div", attrs];
  },

  addNodeView() {
    return ({ node }) => {
      const dom = document.createElement("div");
      dom.setAttribute("data-label", node.attrs.label || "Jinja Block");
      dom.setAttribute("contenteditable", "false");
      dom.className = "jinja-block-placeholder";
      const lockSpan = document.createElement("span");
      lockSpan.className = "jinja-block-placeholder-lock";
      lockSpan.textContent = " (locked)";
      dom.appendChild(lockSpan);
      return { dom };
    };
  },
});
