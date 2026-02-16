"use client";

import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

const MODAL_ROOT_ATTR = "data-modal-root";

export type ModalProps = {
  open: boolean;
  title: string;
  children: React.ReactNode;
  onClose: () => void;
  wide?: boolean;
  zIndex?: number;
  /** When true, closing attempts show unsaved-changes confirmation. Default true. Set false for view-only modals. */
  confirmOnClose?: boolean;
  /** When true, closing attempts (close button, overlay, Escape) show an unsaved-changes confirmation. Requires onSave when confirmOnClose is true. */
  isDirty?: boolean;
  /** Called when user chooses "Save" in the unsaved-changes dialog. Should perform save (and typically close on success). */
  onSave?: () => void | Promise<void>;
  /** Optional ref to receive requestClose. Call requestCloseRef.current?.() from e.g. a Cancel button to trigger the same close flow (including confirmation if dirty). */
  requestCloseRef?: React.MutableRefObject<(() => void) | null>;
};

/**
 * Portal-based modal: renders into a dedicated container appended to body.
 * When open=false returns null and the container is removed so no orphan DOM blocks clicks.
 *
 * Optional unsaved-changes protection: pass isDirty and onSave. When user tries to close (close button,
 * overlay click, Escape) and isDirty is true, a confirmation dialog appears: Save | Discard | Cancel.
 */
export default function Modal({
  open,
  title,
  children,
  onClose,
  wide,
  zIndex = 9999,
  confirmOnClose = true,
  isDirty = false,
  onSave,
  requestCloseRef,
}: ModalProps) {
  const [container, setContainer] = useState<HTMLDivElement | null>(null);
  const [showUnsavedConfirm, setShowUnsavedConfirm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const shouldConfirmClose = confirmOnClose && isDirty && Boolean(onSave);

  const handleCloseRequest = useCallback(() => {
    if (shouldConfirmClose) {
      setSaveError(null);
      setShowUnsavedConfirm(true);
    } else {
      onClose();
    }
  }, [shouldConfirmClose, onClose]);

  const handleSave = useCallback(async () => {
    if (!onSave) return;
    setSaving(true);
    setSaveError(null);
    try {
      await onSave();
      setShowUnsavedConfirm(false);
      // Parent's save handler typically calls onClose on success
      onClose();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setSaveError(msg || "Save failed");
    } finally {
      setSaving(false);
    }
  }, [onSave, onClose]);

  const handleDiscard = useCallback(() => {
    setShowUnsavedConfirm(false);
    onClose();
  }, [onClose]);

  const handleCancelConfirm = useCallback(() => {
    setShowUnsavedConfirm(false);
  }, []);

  useEffect(() => {
    if (requestCloseRef) {
      requestCloseRef.current = handleCloseRequest;
      return () => {
        requestCloseRef.current = null;
      };
    }
  }, [requestCloseRef, handleCloseRequest]);

  useLayoutEffect(() => {
    if (!open) {
      setContainer(null);
      setShowUnsavedConfirm(false);
      setSaving(false);
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
      if (e.key !== "Escape") return;
      if (showUnsavedConfirm) {
        handleCancelConfirm();
      } else {
        handleCloseRequest();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, showUnsavedConfirm, handleCloseRequest, handleCancelConfirm]);

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

  const unsavedConfirmDialog = showUnsavedConfirm ? (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="unsaved-confirm-title"
      style={{
        position: "absolute",
        inset: 0,
        background: "rgba(255,255,255,0.92)",
        backdropFilter: "blur(8px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1,
        padding: 24,
      }}
    >
      <div
        style={{
          maxWidth: 360,
          padding: 24,
          background: "#fff",
          borderRadius: 16,
          boxShadow: "0 20px 60px rgba(0,0,0,0.15)",
          border: "1px solid #e5e5e7",
        }}
      >
        <div id="unsaved-confirm-title" style={{ fontWeight: 600, marginBottom: 8, fontSize: 16 }}>
          Unsaved changes
        </div>
        <div style={{ fontSize: 14, color: "#444", marginBottom: 16 }}>
          You have unsaved changes. Save before closing?
        </div>
        {saveError && (
          <div style={{ color: "#c00", fontSize: 14, marginBottom: 16, whiteSpace: "pre-wrap" }}>
            {saveError}
          </div>
        )}
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", flexWrap: "wrap" }}>
          <button type="button" onClick={handleCancelConfirm} disabled={saving}>
            Cancel
          </button>
          <button type="button" onClick={handleDiscard} disabled={saving}>
            Discard
          </button>
          <button type="button" className="primary" onClick={handleSave} disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  ) : null;

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
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) handleCloseRequest();
      }}
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
          position: "relative",
        }}
        onClick={(e) => e.stopPropagation()}
        onMouseDown={(e) => e.stopPropagation()}
        onPointerDown={(e) => e.stopPropagation()}
      >
        <div style={{ padding: 18, borderBottom: "1px solid #eee", display: "flex", justifyContent: "space-between", flexShrink: 0 }}>
          <div id="modal-title" style={{ fontWeight: 600 }}>{title}</div>
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              handleCloseRequest();
            }}
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        <div style={{ padding: 18, overflow: "auto", flex: 1, minHeight: 0 }}>{children}</div>
        {unsavedConfirmDialog}
      </div>
    </div>
  );

  return createPortal(overlay, container);
}
