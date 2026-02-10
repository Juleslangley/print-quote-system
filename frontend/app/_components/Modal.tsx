"use client";

import { useEffect, useLayoutEffect, useState } from "react";
import { createPortal } from "react-dom";

const MODAL_ROOT_ATTR = "data-modal-root";

/**
 * Portal-based modal: renders into a dedicated container appended to body.
 * When open=false returns null and the container is removed so no orphan DOM blocks clicks.
 */
export default function Modal({
  open,
  title,
  children,
  onClose,
  wide,
  zIndex = 9999,
}: {
  open: boolean;
  title: string;
  children: React.ReactNode;
  onClose: () => void;
  wide?: boolean;
  zIndex?: number;
}) {
  const [container, setContainer] = useState<HTMLDivElement | null>(null);

  useLayoutEffect(() => {
    if (!open) {
      setContainer(null);
      return;
    }
    const el = document.createElement("div");
    el.setAttribute(MODAL_ROOT_ATTR, "true");
    document.body.appendChild(el);
    setContainer(el);
    return () => {
      if (el.parentNode) el.parentNode.removeChild(el);
      setContainer(null);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prevOverflow;
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  useEffect(() => {
    if (typeof window === "undefined" || process.env.NODE_ENV !== "development") return;
    (window as unknown as { __modalDebug?: () => number }).__modalDebug = () =>
      document.querySelectorAll(`[${MODAL_ROOT_ATTR}="true"]`).length;
  }, []);

  if (typeof document === "undefined") return null;
  if (!open) return null;
  if (!container) return null;

  const safePad = "max(24px, env(safe-area-inset-top, 0px))";
  const safePadBottom = "max(24px, env(safe-area-inset-bottom, 0px))";
  const safePadLeft = "max(24px, env(safe-area-inset-left, 0px))";
  const safePadRight = "max(24px, env(safe-area-inset-right, 0px))";

  const overlay = (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.25)",
        backdropFilter: "blur(10px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
        paddingTop: safePad,
        paddingBottom: safePadBottom,
        paddingLeft: safePadLeft,
        paddingRight: safePadRight,
        zIndex,
        boxSizing: "border-box",
      }}
      onClick={onClose}
      onMouseDown={onClose}
    >
      <div
        style={{
          width: wide ? "min(900px, 100%)" : "min(520px, 100%)",
          maxHeight: "min(90vh, calc(100vh - 48px))",
          background: "#fff",
          borderRadius: 20,
          boxShadow: "0 30px 80px rgba(0,0,0,0.2)",
          border: "1px solid #e5e5e7",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          boxSizing: "border-box",
        }}
        onClick={(e) => e.stopPropagation()}
        onMouseDown={(e) => e.stopPropagation()}
        onPointerDown={(e) => e.stopPropagation()}
      >
        <div style={{ padding: 18, borderBottom: "1px solid #eee", display: "flex", justifyContent: "space-between", flexShrink: 0 }}>
          <div id="modal-title" style={{ fontWeight: 600 }}>{title}</div>
          <button type="button" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div style={{ padding: 18, overflow: "auto", flex: 1, minHeight: 0 }}>{children}</div>
      </div>
    </div>
  );

  return createPortal(overlay, container);
}
