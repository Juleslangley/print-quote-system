"use client";

import React, { useState, useRef } from "react";

export default function Tooltip({
  children,
  content,
}: {
  children: React.ReactElement;
  content: string;
}) {
  const [visible, setVisible] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const show = () => {
    timeoutRef.current = setTimeout(() => setVisible(true), 300);
  };

  const hide = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    setVisible(false);
  };

  return (
    <span
      className="qb-tooltip-wrap"
      onMouseEnter={show}
      onMouseLeave={hide}
      style={{ position: "relative", display: "inline-flex" }}
    >
      {children}
      {visible && (
        <span className="qb-tooltip" role="tooltip">
          {content}
        </span>
      )}
    </span>
  );
}
