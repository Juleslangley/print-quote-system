import { Node } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";

/**
 * Atomic PO Totals block for purchase_order templates.
 * Serializes to: <div data-jinja-block="po_totals" class="po-totals-block"></div>
 */
export const PoTotalsBlock = Node.create({
  name: "poTotalsBlock",
  group: "block",
  atom: true,
  selectable: true,
  draggable: false,

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey("poTotalsBlockPreventDelete"),
        props: {
          handleKeyDown: (view, event) => {
            if (event.key !== "Backspace" && event.key !== "Delete") return false;
            const { state } = view;
            const $pos = state.selection.$anchor;
            for (let d = $pos.depth; d > 0; d--) {
              const node = $pos.node(d);
              if (node.type.name === "poTotalsBlock") {
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

  parseHTML() {
    return [
      { tag: 'div[data-jinja-block="po_totals"]', priority: 70 },
      { tag: "div.po-totals-block", priority: 65 },
    ];
  },

  renderHTML() {
    return [
      "div",
      {
        "data-jinja-block": "po_totals",
        class: "po-totals-block",
      },
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
      title.textContent = "PO Totals (locked)";

      const hint = document.createElement("div");
      hint.className = "locked-hint";
      hint.textContent = "Subtotal, VAT, and total render automatically.";

      dom.appendChild(title);
      dom.appendChild(hint);

      return {
        dom,
        ignoreMutation: () => true,
        stopEvent: () => true,
      };
    };
  },
});
