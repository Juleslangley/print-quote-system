"use client";

import React, { createContext, useCallback, useContext, useState } from "react";
import { createPortal } from "react-dom";

type ToastItem = { id: number; message: string; variant?: "default" | "success" | "warning" };

const ToastContext = createContext<((msg: string, variant?: ToastItem["variant"]) => void) | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  return ctx ?? (() => {});
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextIdRef = React.useRef(0);

  const toast = useCallback((message: string, variant: ToastItem["variant"] = "default") => {
    const id = nextIdRef.current++;
    setToasts((prev) => [...prev, { id, message, variant }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3000);
  }, []);

  return (
    <ToastContext.Provider value={toast}>
      {children}
      {typeof document !== "undefined" &&
        createPortal(
          <div
            style={{
              position: "fixed",
              bottom: 24,
              right: 24,
              zIndex: 10000,
              display: "flex",
              flexDirection: "column",
              gap: 8,
              pointerEvents: "none",
            }}
          >
            {toasts.map((t) => (
              <div
                key={t.id}
                className="qb-toast"
                data-variant={t.variant}
                style={{
                  padding: "12px 16px",
                  borderRadius: 10,
                  background: t.variant === "success" ? "#d4edda" : t.variant === "warning" ? "#fff3cd" : "#1d1d1f",
                  color: t.variant === "success" || t.variant === "warning" ? "#1d1d1f" : "#fff",
                  fontSize: 14,
                  boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
                  animation: "qb-toast-in 0.2s ease",
                }}
              >
                {t.message}
              </div>
            ))}
          </div>,
          document.body
        )}
    </ToastContext.Provider>
  );
}
