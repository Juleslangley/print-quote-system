"use client";

import { useCallback, useRef, useState } from "react";

/**
 * Deep equality check for primitives, plain objects, arrays, null, undefined.
 * Does not support Date, RegExp, or other complex types.
 */
export function deepEqual(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (a == null || b == null) return a === b;
  if (typeof a !== typeof b) return false;

  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) return false;
    return a.every((item, i) => deepEqual(item, b[i]));
  }

  if (Array.isArray(a) || Array.isArray(b)) return false;
  if (typeof a === "object" && typeof b === "object") {
    const keysA = Object.keys(a);
    const keysB = Object.keys(b);
    if (keysA.length !== keysB.length) return false;
    return keysA.every((k) => keysB.includes(k) && deepEqual((a as Record<string, unknown>)[k], (b as Record<string, unknown>)[k]));
  }

  return false;
}

export type UseDirtyStateReturn<T> = {
  baseline: T | undefined;
  setBaseline: (value: T | undefined) => void;
  isDirty: (current: T | undefined) => boolean;
};

/**
 * Hook for tracking dirty state of object-based forms.
 * - baseline: the original/snapshot value (set when modal loads entity)
 * - setBaseline: update the baseline (e.g. when switching from create → edit)
 * - isDirty(current): true if current differs from baseline (returns false if baseline not set)
 */
export function useDirtyState<T>(initial?: T): UseDirtyStateReturn<T> {
  const [baseline, setBaselineState] = useState<T | undefined>(initial);
  const baselineRef = useRef<T | undefined>(baseline);
  baselineRef.current = baseline;

  const setBaseline = useCallback((value: T | undefined) => {
    setBaselineState(value);
    baselineRef.current = value;
  }, []);

  const isDirty = useCallback((current: T | undefined): boolean => {
    const base = baselineRef.current;
    if (base === undefined) return false;
    return !deepEqual(current, base);
  }, []);

  return { baseline, setBaseline, isDirty };
}
