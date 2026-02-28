"use client";

import type { CSSProperties } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useEditor, EditorContent, type Editor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import { Node as TiptapNode } from "@tiptap/core";
import { JINJA_FIELDS } from "./InsertFieldDropdown";
import { JinjaBlock } from "./tiptap/JinjaBlock";
import { PoLinesBlock, PO_LINES_TEMPLATE_HTML } from "./tiptap/PoLinesBlock";
import { PoTotalsBlock } from "./tiptap/PoTotalsBlock";
import { BarcodeBlockAtom } from "./tiptap/BarcodeBlockAtom";
import { createPoLinesBlockUniquenessExtension } from "./tiptap/PoLinesBlockUniquenessPlugin";


const PO_TOTALS_JINJA = `<div class="po-totals-wrap"><table class="po-totals" role="table" aria-label="Totals"><tbody><tr><td>Subtotal</td><td class="right">£{{ '%.2f'|format(po.subtotal_gbp or 0) }}</td></tr><tr><td>VAT</td><td class="right">£{{ '%.2f'|format(po.vat_gbp or 0) }}</td></tr><tr class="grand"><td>Total</td><td class="right">£{{ '%.2f'|format(po.total_gbp or 0) }}</td></tr></tbody></table></div>`;

const STORE_PACKING_JINJA = `<table class="store-packing-table"><tbody>{% for store in batch.stores %}<tr><td>{{ store.store_name }}</td></tr>{% for item in store.line_items %}<tr><td>{{ item.component }}</td><td>{{ item.description }}</td><td>{{ item.qty }}</td></tr>{% endfor %}{% endfor %}</tbody></table>`;

const TOTALS_JINJA = `<div class="totals-block">£{{ (po.total_gbp or quote.total_sell or 0)|default(0) }}</div>`;
const BARCODE_JINJA = `<div class="barcode-block">{{ job.barcode_svg }}</div>`;

/** Guard: dom must be an Element; ProseMirror can pass non-Element nodes (Text, Comment, Fragment). */
function asElement(dom: unknown): Element | null {
  try {
    if (!dom || (dom as Node).nodeType !== 1) return null;
    const el = dom as Element;
    if (typeof el.hasAttribute !== "function") return null;
    if (el.hasAttribute("contenteditable")) return null;
    if (typeof el.getAttribute !== "function") return null;
    return el;
  } catch {
    return null;
  }
}

function createJinjaBlockNode(name: string, label: string, jinjaOutput: string) {
  return TiptapNode.create({
    name,
    group: "block",
    atom: true,
    addAttributes() {
      return {
        dataJinjaOutput: {
          default: jinjaOutput,
          parseHTML: (el) => {
            const elem = asElement(el);
            return elem ? elem.getAttribute("data-jinja-output") ?? jinjaOutput : jinjaOutput;
          },
          renderHTML: (attrs) =>
            attrs.dataJinjaOutput ? { "data-jinja-output": attrs.dataJinjaOutput } : {},
        },
      };
    },
    parseHTML() {
      const baseRule = {
        tag: `div[data-type="${name}"]`,
        getAttrs: (dom: Node) => {
          const el = asElement(dom);
          if (!el) return false;
          const raw = el.getAttribute("data-jinja-output");
          return { dataJinjaOutput: raw ?? jinjaOutput };
        },
      };
      const rawSelectors =
        name === "totalsBlock"
          ? [
              {
                tag: "div.po-totals-wrap",
                getAttrs: (dom: Node) => {
                  const el = asElement(dom);
                  if (!el) return false;
                  const table = el.querySelector("table.po-totals");
                  if (!table) return false;
                  return { dataJinjaOutput: el.outerHTML };
                },
              },
              {
                tag: "table.po-totals",
                getAttrs: (dom: Node) => {
                  const el = asElement(dom);
                  if (!el) return false;
                  const wrap = el.closest?.("div.po-totals-wrap");
                  if (wrap) return false;
                  return { dataJinjaOutput: el.outerHTML };
                },
              },
              {
                tag: "div.totals-block",
                getAttrs: (dom: Node) => {
                  const el = asElement(dom);
                  if (!el) return false;
                  return { dataJinjaOutput: el.outerHTML };
                },
              },
            ]
          : [];
      return [baseRule, ...rawSelectors];
    },
    renderHTML({ node }) {
      const html = node.attrs.dataJinjaOutput || jinjaOutput;
      if (typeof document !== "undefined") {
        const wrapper = document.createElement("div");
        wrapper.innerHTML = html;
        if (wrapper.childNodes.length === 1 && wrapper.firstChild) {
          return wrapper.firstChild as HTMLElement;
        }
        return wrapper;
      }
      return [
        "div",
        { "data-type": name, "data-jinja-output": html, class: "jinja-block-editor" },
        ["span", { class: "jinja-block-label" }, label],
      ];
    },
  });
}

const StorePackingTable = createJinjaBlockNode("storePackingTable", "Store Packing Table", STORE_PACKING_JINJA);
const TotalsBlock = createJinjaBlockNode("totalsBlock", "Totals", TOTALS_JINJA);
const BarcodeBlock = createJinjaBlockNode("barcodeBlock", "Barcode", BARCODE_JINJA);

/** Safety rewrite: never emit literal "true". Fix old content before expansion. */
function rewriteJinjaOutputTrue(html: string): string {
  return html.replace(/data-jinja-output="true"/gi, 'data-jinja-output=""');
}

/** Strip stray "true" text or <p>true</p> adjacent to jinja blocks. */
function stripStrayTrue(html: string): string {
  return html
    .replace(/<p>true<\/p>/gi, "")
    .replace(/>\s*true\s*</g, "><");
}

/**
 * For purchase_order: ensure exactly one po_lines block before save.
 * If missing, inserts it and returns the expanded HTML. Call before save.
 */
export function prepareHtmlForSave(editor: Editor | null, docType: string): string {
  if (!editor) return "";
  let raw = editor.getHTML();
  if (docType === "purchase_order") {
    const hasPlaceholder =
      raw.includes('data-jinja-block="po_lines"') ||
      raw.includes("po-lines-block") ||
      raw.includes('data-template-block="po-lines"');
    if (!hasPlaceholder) {
      editor.chain().focus().insertContent({ type: "poLinesBlock" }).run();
      raw = editor.getHTML();
    }
  }
  return expandJinjaBlocks(raw);
}

export function expandJinjaBlocks(html: string): string {
  if (typeof document === "undefined") return html;
  html = rewriteJinjaOutputTrue(html);
  const div = document.createElement("div");
  div.innerHTML = html;
  div.querySelectorAll("[data-jinja-output]").forEach((el) => {
    const attr = el.getAttribute("data-jinja-output") ?? "";
    const replacement =
      attr === "" || attr === "true"
        ? (el as HTMLElement).innerHTML
        : attr;
    if (replacement) {
      const frag = document.createElement("template");
      frag.innerHTML = replacement;
      el.replaceWith(...Array.from(frag.content.childNodes));
    }
  });
  let result = div.innerHTML;
  result = stripStrayTrue(result);
  return result;
}

export function useDocumentTemplateEditor(
  initialHtml: string,
  initialJson: string | null,
  docType: string,
  onUpdate?: (html: string, json: string) => void
) {
  const baseExtensions = [
    StarterKit,
    Placeholder.configure({ placeholder: "Start typing or use Insert Field / blocks…" }),
    JinjaBlock,
    StorePackingTable,
    TotalsBlock,
    BarcodeBlock,
  ];
  const isPo = docType === "purchase_order";
  const isProductionOrder = docType === "production_order";
  const extensions = isPo
    ? [
        ...baseExtensions,
        PoLinesBlock,
        PoTotalsBlock,
        BarcodeBlockAtom,
        createPoLinesBlockUniquenessExtension(docType),
      ]
    : isProductionOrder
      ? [...baseExtensions, BarcodeBlockAtom]
      : baseExtensions;

  return useEditor({
    immediatelyRender: false,
    extensions,
    content: (() => {
      if (initialJson) {
        try {
          return JSON.parse(initialJson);
        } catch {
          return initialHtml || undefined;
        }
      }
      return initialHtml || undefined;
    })(),
    onUpdate: ({ editor }) => {
      const json = JSON.stringify(editor.getJSON());
      const rawHtml = editor.getHTML();
      const html = expandJinjaBlocks(rawHtml);
      onUpdate?.(html, json);
    },
    editorProps: {
      attributes: { class: "doc-template-editor" },
      handleDOMEvents: {
        paste: (_view, event) => {
          const html = event.clipboardData?.getData("text/html");
          if (html?.includes("script")) {
            event.preventDefault();
            return true;
          }
        },
      },
    },
  });
}

const TEXTAREA_STYLE: CSSProperties = {
  fontFamily: "ui-monospace, monospace",
  fontSize: 12,
  width: "100%",
  resize: "vertical",
};

function getBlockSnippet(blockType: string, docType: string): string {
  switch (blockType) {
    case "lineItemsTable": return PO_LINES_TEMPLATE_HTML;
    case "storePackingTable": return STORE_PACKING_JINJA;
    case "totalsBlock": return docType === "purchase_order" ? PO_TOTALS_JINJA : TOTALS_JINJA;
    case "barcodeBlock": return BARCODE_JINJA;
    default: return "";
  }
}

type DocumentTemplateEditorProps = {
  editor: Editor | null;
  docType: string;
  editorMode: "raw" | "visual";
  engine?: string;
  onHtmlChange?: (html: string) => void;
  templateHtml?: string;
  rawTextareaTestId?: string;
};

export function DocumentTemplateEditor({
  editor,
  docType,
  editorMode,
  engine = "html_jinja",
  onHtmlChange,
  templateHtml = "",
  rawTextareaTestId,
}: DocumentTemplateEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isJinja = engine === "html_jinja";

  const insertAtCursor = useCallback(
    (text: string) => {
      const ta = textareaRef.current;
      if (!ta) {
        onHtmlChange?.((templateHtml || "") + text);
        return;
      }
      const start = ta.selectionStart;
      const end = ta.selectionEnd;
      const newVal = templateHtml.slice(0, start) + text + templateHtml.slice(end);
      onHtmlChange?.(newVal);
      const newPos = start + text.length;
      requestAnimationFrame(() => {
        ta.focus();
        ta.selectionStart = ta.selectionEnd = newPos;
      });
    },
    [templateHtml, onHtmlChange]
  );

  const onInsertFieldRaw = useCallback(
    (token: string) => insertAtCursor(token),
    [insertAtCursor]
  );

  const onInsertBlockRaw = useCallback(
    (blockType: string) => {
      const snippet = getBlockSnippet(blockType, docType);
      if (snippet) insertAtCursor(snippet);
    },
    [insertAtCursor, docType]
  );

  const onInsertFieldVisual = useCallback(
    (token: string) => {
      if (!editor) return;
      editor.chain().focus().insertContent(token).run();
    },
    [editor]
  );

  const findBlockPos = useCallback(
    (typeName: string): number | null => {
      if (!editor) return null;
      let pos: number | null = null;
      editor.state.doc.descendants((node, p) => {
        if (node.type.name === typeName && pos === null) {
          pos = p;
        }
      });
      return pos;
    },
    [editor]
  );

  const onInsertBlockVisual = useCallback(
    (blockType: string) => {
      if (!editor) return;
      const totalsJinja = docType === "purchase_order" ? PO_TOTALS_JINJA : TOTALS_JINJA;
      if (blockType === "lineItemsTable") {
        if (docType === "purchase_order") {
          const existingPos = findBlockPos("poLinesBlock");
          if (existingPos !== null) {
            editor.chain().focus().setTextSelection(existingPos).scrollIntoView().run();
            return;
          }
          editor.chain().focus().insertContent({ type: "poLinesBlock" }).run();
          return;
        }
        const wrapper = `<div data-jinja-output="">${PO_LINES_TEMPLATE_HTML}</div>`;
        editor.chain().focus().insertContent(wrapper, { parseOptions: { preserveWhitespace: "full" } }).run();
      } else if (blockType === "storePackingTable") {
        editor.chain().focus().insertContent({ type: "storePackingTable" }).run();
      } else if (blockType === "totalsBlock") {
        if (docType === "purchase_order") {
          const existingPos = findBlockPos("poTotalsBlock");
          if (existingPos !== null) {
            editor.chain().focus().setTextSelection(existingPos).scrollIntoView().run();
            return;
          }
          editor.chain().focus().insertContent({ type: "poTotalsBlock" }).run();
          return;
        }
        editor
          .chain()
          .focus()
          .insertContent({
            type: "totalsBlock",
            attrs: { dataJinjaOutput: totalsJinja },
          })
          .run();
      } else if (blockType === "barcodeBlock") {
        if (docType === "purchase_order" || docType === "production_order") {
          editor.chain().focus().insertContent({ type: "barcodeBlockAtom" }).run();
          return;
        }
        editor.chain().focus().insertContent({ type: "barcodeBlock" }).run();
      }
    },
    [editor, docType, findBlockPos]
  );

  if (isJinja || editorMode === "raw") {
    return (
      <div className="doc-template-editor-wrap doc-template-textarea-mode">
        {!isJinja && (
          <div className="doc-editor-toolbar">
            <InsertFieldDropdown onSelect={onInsertFieldRaw} docType={docType} />
            <div className="toolbar-sep" />
            <BlockMenu onSelect={onInsertBlockRaw} />
          </div>
        )}
        <textarea
          data-testid={isJinja ? "jinja-raw-editor" : rawTextareaTestId}
          ref={textareaRef}
          value={templateHtml}
          onChange={(e) => onHtmlChange?.(e.target.value)}
          placeholder="<div>{{ po.po_number }}… {% if lines %}…{% endif %} …</div>"
          rows={18}
          style={{
            ...TEXTAREA_STYLE,
            height: 420,
            minHeight: 200,
            whiteSpace: "pre",
            overflowWrap: "normal",
            wordBreak: "normal",
          }}
          spellCheck={false}
          wrap="off"
        />
      </div>
    );
  }

  if (!editor) return null;

  return (
    <div className="doc-template-editor-wrap">
      <div className="doc-editor-toolbar">
        <InsertFieldDropdown onSelect={onInsertFieldVisual} docType={docType} />
        <div className="toolbar-sep" />
        <BlockMenu onSelect={onInsertBlockVisual} />
      </div>
      <EditorContent editor={editor} />
    </div>
  );
}

function InsertFieldDropdown({
  onSelect,
  docType,
}: {
  onSelect: (token: string) => void;
  docType: string;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const fields = JINJA_FIELDS[docType as keyof typeof JINJA_FIELDS] || JINJA_FIELDS.purchase_order;

  useEffect(() => {
    if (!open) return;
    const onOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as globalThis.Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onOutside);
    return () => document.removeEventListener("mousedown", onOutside);
  }, [open]);

  return (
    <div ref={ref} className="insert-field-dropdown">
      <button type="button" onClick={() => setOpen((o) => !o)} className="toolbar-btn">
        Insert Field ▼
      </button>
      {open && (
        <div className="dropdown-menu">
          {fields.map((f) => (
            <button
              key={f.token}
              type="button"
              className="dropdown-item"
              onClick={() => {
                onSelect(f.token);
                setOpen(false);
              }}
            >
              {f.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function BlockMenu({ onSelect }: { onSelect: (block: string) => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as globalThis.Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onOutside);
    return () => document.removeEventListener("mousedown", onOutside);
  }, [open]);

  const blocks = [
    { id: "lineItemsTable", label: "Line Items Table" },
    { id: "storePackingTable", label: "Store Packing Table" },
    { id: "totalsBlock", label: "Totals Block" },
    { id: "barcodeBlock", label: "Barcode Block" },
  ];

  return (
    <div ref={ref} className="block-menu">
      <button type="button" onClick={() => setOpen((o) => !o)} className="toolbar-btn">
        Insert Block ▼
      </button>
      {open && (
        <div className="dropdown-menu">
          {blocks.map((b) => (
            <button
              key={b.id}
              type="button"
              className="dropdown-item"
              onClick={() => {
                onSelect(b.id);
                setOpen(false);
              }}
            >
              {b.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
