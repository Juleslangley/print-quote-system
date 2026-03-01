"use client";

import React, { useEffect, useCallback } from "react";
import { createPortal } from "react-dom";

export type DrawerProps = {
  open: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  children: React.ReactNode;
  width?: number;
};

export default function Drawer({ open, onClose, title, children, width = 420 }: DrawerProps) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose]
  );

  useEffect(() => {
    if (open) {
      document.addEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [open, handleKeyDown]);

  if (!open) return null;

  return typeof document !== "undefined"
    ? createPortal(
        <div className="qb-drawer-overlay" onClick={onClose}>
          <div
            className="qb-drawer-panel"
            style={{ width: Math.min(width, window.innerWidth - 24) }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="qb-drawer-header">
              {title && <div className="qb-drawer-title">{title}</div>}
              <button
            type="button"
            className="qb-drawer-close qb-ghost-btn"
            onClick={onClose}
            aria-label="Close"
          >
            ×
          </button>
            </div>
            <div className="qb-drawer-body">{children}</div>
          </div>
        </div>,
        document.body
      )
    : null;
}
