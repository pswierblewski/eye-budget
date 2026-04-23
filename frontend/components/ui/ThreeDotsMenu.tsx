"use client";

import React, { useRef, useEffect, useState, useLayoutEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import { MoreHorizontal } from "lucide-react";
import { clsx } from "clsx";

function getScrollableAncestors(start: Element | null): Element[] {
  const out: Element[] = [];
  let el: Element | null = start;
  while (el) {
    const st = getComputedStyle(el);
    const oy = st.overflowY;
    const ox = st.overflowX;
    if (
      /auto|scroll|overlay/.test(oy) ||
      /auto|scroll|overlay/.test(ox) ||
      st.overflow === "auto"
    ) {
      out.push(el);
    }
    el = el.parentElement;
  }
  return out;
}

export interface ThreeDotsMenuItem {
  label: string;
  onClick: () => void;
  variant?: "default" | "danger";
  separator?: boolean;
  disabled?: boolean;
}

interface ThreeDotsMenuProps {
  items: ThreeDotsMenuItem[];
  variant?: "inline" | "outlined";
  title?: string;
  /** "right" – menu wyrównane do prawej krawędzi przycisku (rośnie w lewo). "left" – do lewej (rośnie w prawo; mniej obcina w lewej kolumnie / przy sidebarze). */
  align?: "right" | "left";
  className?: string;
}

const MENU_EST_W = 200;
const MENU_PAD = 4;

export function ThreeDotsMenu({
  items,
  variant = "inline",
  title = "Więcej opcji",
  align = "right",
  className,
}: ThreeDotsMenuProps) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState({ top: 0, left: 0 });
  const triggerRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const updatePosition = useCallback(() => {
    const t = triggerRef.current;
    if (!t) return;
    const r = t.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    let left: number;
    if (align === "right") {
      left = r.right - MENU_EST_W;
    } else {
      left = r.left;
    }
    left = Math.max(8, Math.min(left, vw - MENU_EST_W - 8));
    let top = r.bottom + MENU_PAD;
    const menuH = menuRef.current?.offsetHeight ?? 120;
    if (top + menuH > vh - 8) {
      top = Math.max(8, r.top - menuH - MENU_PAD);
    }
    setPos({ top, left });
  }, [align]);

  useLayoutEffect(() => {
    if (!open) return;
    updatePosition();
    const id = requestAnimationFrame(() => updatePosition());
    return () => cancelAnimationFrame(id);
  }, [open, updatePosition, items.length]);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      const el = e.target as Node;
      if (triggerRef.current?.contains(el) || menuRef.current?.contains(el)) return;
      setOpen(false);
    };
    const onScrollClose = () => setOpen(false);
    document.addEventListener("mousedown", onDown, true);
    window.addEventListener("resize", updatePosition);
    const ancs = getScrollableAncestors(triggerRef.current);
    ancs.forEach((n) =>
      n.addEventListener("scroll", onScrollClose, { capture: true, passive: true })
    );
    return () => {
      document.removeEventListener("mousedown", onDown, true);
      window.removeEventListener("resize", updatePosition);
      ancs.forEach((n) =>
        n.removeEventListener("scroll", onScrollClose, { capture: true } as never)
      );
    };
  }, [open, updatePosition]);

  const button = (
    <div ref={triggerRef} className={clsx("relative", className)}>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        title={title}
        className={clsx(
          "transition-colors",
          variant === "outlined"
            ? "px-2.5 py-1.5 rounded-md border border-gray-200 text-gray-500 hover:bg-gray-50"
            : "p-1 rounded text-gray-400 hover:text-gray-700 hover:bg-gray-100"
        )}
      >
        <MoreHorizontal className="h-4 w-4" />
      </button>
    </div>
  );

  const menu = open
    ? createPortal(
        <div
          ref={menuRef}
          className={clsx(
            "fixed z-[200] min-w-[160px] max-w-[min(20rem,calc(100vw-1rem))] bg-white border border-gray-200 rounded-lg shadow-lg py-1"
          )}
          style={{ top: pos.top, left: pos.left }}
          onClick={(e) => e.stopPropagation()}
        >
          {items.map((item, i) => (
            <React.Fragment key={i}>
              {item.separator && <div className="border-t border-gray-100 my-1" />}
              <button
                type="button"
                onClick={() => {
                  item.onClick();
                  setOpen(false);
                }}
                disabled={item.disabled}
                className={clsx(
                  "w-full text-left text-sm px-4 py-2 transition-colors disabled:opacity-50",
                  item.variant === "danger"
                    ? "text-red-600 hover:bg-red-50"
                    : "text-gray-700 hover:bg-gray-50"
                )}
              >
                {item.label}
              </button>
            </React.Fragment>
          ))}
        </div>,
        document.body
      )
    : null;

  return (
    <>
      {button}
      {menu}
    </>
  );
}
