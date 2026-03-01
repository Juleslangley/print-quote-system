"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import { createPortal } from "react-dom";

export type CommandItem = {
  id: string;
  label: string;
  subtitle?: string;
  onSelect: () => void;
};

export type CommandPaletteProps = {
  open: boolean;
  onClose: () => void;
  items: CommandItem[];
  placeholder?: string;
};

export default function CommandPalette({
  open,
  onClose,
  items,
  placeholder = "Type a command or search…",
}: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const filtered = items.filter(
    (i) =>
      !query ||
      i.label.toLowerCase().includes(query.toLowerCase())
  );
  const clampedIdx = Math.min(selectedIdx, Math.max(0, filtered.length - 1));

  useEffect(() => {
    if (open) {
      setQuery("");
      setSelectedIdx(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  useEffect(() => {
    setSelectedIdx(0);
  }, [query]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIdx((i) => Math.min(i + 1, filtered.length - 1));
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIdx((i) => Math.max(i - 1, 0));
        return;
      }
      if (e.key === "Enter" && filtered[clampedIdx]) {
        e.preventDefault();
        filtered[clampedIdx].onSelect();
        onClose();
      }
    },
    [filtered, clampedIdx, onClose]
  );

  useEffect(() => {
    const el = listRef.current;
    if (!el || !filtered[clampedIdx]) return;
    const item = el.querySelector(`[data-idx="${clampedIdx}"]`);
    item?.scrollIntoView({ block: "nearest" });
  }, [clampedIdx, filtered.length]);

  if (!open) return null;

  return typeof document !== "undefined"
    ? createPortal(
        <div
          className="qb-command-palette-overlay"
          onClick={onClose}
        >
          <div
            className="qb-command-palette"
            onClick={(e) => e.stopPropagation()}
          >
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
            />
            <div ref={listRef} className="qb-command-palette-list">
              {filtered.map((item, idx) => (
                <button
                  key={item.id}
                  data-idx={idx}
                  type="button"
                  className={`qb-command-item ${idx === clampedIdx ? "qb-selected" : ""}`}
                  onClick={() => {
                    item.onSelect();
                    onClose();
                  }}
                  onMouseEnter={() => setSelectedIdx(idx)}
                >
                  {item.label}
                  {item.subtitle && (
                    <span className="subtle" style={{ marginLeft: 8 }}>{item.subtitle}</span>
                  )}
                </button>
              ))}
              {filtered.length === 0 && (
                <div style={{ padding: 16, color: "#6e6e73", fontSize: 14 }}>
                  No commands found
                </div>
              )}
            </div>
          </div>
        </div>,
        document.body
      )
    : null;
}
