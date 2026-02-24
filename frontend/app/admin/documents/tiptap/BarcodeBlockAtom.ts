import { Node } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";

/**
 * Atomic Barcode block. Serializes to: <div data-jinja-block="barcode" class="barcode-block"></div>
 * Used for production_order and other doc types with job.barcode_svg.
 */
export const BarcodeBlockAtom = Node.create({
  name: "barcodeBlockAtom",
  group: "block",
  atom: true,
  selectable: true,
  draggable: false,

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey("barcodeBlockAtomPreventDelete"),
        props: {
          handleKeyDown: (view, event) => {
            if (event.key !== "Backspace" && event.key !== "Delete") return false;
            const { state } = view;
            const $pos = state.selection.$anchor;
            for (let d = $pos.depth; d > 0; d--) {
              const node = $pos.node(d);
              if (node.type.name === "barcodeBlockAtom") {
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
      { tag: 'div[data-jinja-block="barcode"]', priority: 70 },
      { tag: "div.barcode-block-atom", priority: 65 },
    ];
  },

  renderHTML() {
    return [
      "div",
      {
        "data-jinja-block": "barcode",
        class: "barcode-block-atom",
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
      title.textContent = "Barcode (locked)";

      const hint = document.createElement("div");
      hint.className = "locked-hint";
      hint.textContent = "Job barcode SVG renders automatically.";

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
