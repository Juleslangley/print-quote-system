import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";

function countNodeType(
  doc: { descendants: (f: (node: { type: { name: string } }) => void) => void },
  typeName: string
): number {
  let count = 0;
  doc.descendants((node) => {
    if (node.type.name === typeName) count++;
  });
  return count;
}

/** Block types that must be unique per doc (purchase_order). */
const UNIQUE_BLOCK_TYPES = ["poLinesBlock", "poTotalsBlock"];

/**
 * For purchase_order templates: reject transactions that would result in >1
 * poLinesBlock or >1 poTotalsBlock.
 */
export function createPoLinesBlockUniquenessExtension(docType: string) {
  return Extension.create({
    name: "poLinesBlockUniqueness",

    addProseMirrorPlugins() {
      if (docType !== "purchase_order") return [];
      return [
        new Plugin({
          key: new PluginKey("poLinesBlockUniqueness"),
          filterTransaction: (tr) => {
            if (!tr.docChanged) return true;
            const newDoc = tr.doc;
            for (const typeName of UNIQUE_BLOCK_TYPES) {
              if (countNodeType(newDoc, typeName) > 1) return false;
            }
            return true;
          },
        }),
      ];
    },
  });
}
