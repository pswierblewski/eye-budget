"use client";

import { useState, useEffect, useRef, useCallback } from "react";

interface ReceiptImageViewerProps {
  scanId: number;
  refreshKey?: number;
  onReuploadImage?: () => Promise<void>;
}

export function ReceiptImageViewer({ scanId, refreshKey = 0, onReuploadImage }: ReceiptImageViewerProps) {
  const [error, setError] = useState(false);
  const [reuploading, setReuploading] = useState(false);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Zoom / pan state
  const [scale, setScale] = useState(1);
  const [translate, setTranslate] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);

  // Refs hold up-to-date values without causing stale closures in event handlers
  const scaleRef = useRef(1);
  const translateRef = useRef({ x: 0, y: 0 });
  const dragStartRef = useRef<{ mx: number; my: number; tx: number; ty: number } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Resolve the image URL: try presigned MinIO URL first (fastest — browser goes
  // directly to MinIO), fall back to the Next.js proxy route if unavailable.
  useEffect(() => {
    setLoading(true);
    setError(false);
    setImageUrl(null);

    let cancelled = false;
    const cacheBust = refreshKey > 0 ? `?bust=${refreshKey}` : "";

    fetch(`/api/receipts/${scanId}/image-url${cacheBust}`)
      .then((res) => {
        if (!res.ok) throw new Error("no-presigned-url");
        return res.json();
      })
      .then((data: { url: string }) => {
        if (!cancelled) setImageUrl(data.url);
      })
      .catch(() => {
        // MinIO not publicly accessible — fall back to the Next.js proxy.
        if (!cancelled)
          setImageUrl(
            `/api/receipts/${scanId}/image${refreshKey > 0 ? `?t=${refreshKey}` : ""}`
          );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [scanId, refreshKey]);

  // ── Zoom / pan handlers ──────────────────────────────────────────────────

  const applyTransform = useCallback((newScale: number, newTx: number, newTy: number) => {
    scaleRef.current = newScale;
    translateRef.current = { x: newTx, y: newTy };
    setScale(newScale);
    setTranslate({ x: newTx, y: newTy });
  }, []);

  // Scroll-to-zoom — cursor-centred
  const handleWheel = useCallback(
    (e: WheelEvent) => {
      e.preventDefault();
      const container = containerRef.current;
      if (!container) return;
      const rect = container.getBoundingClientRect();
      const cx = e.clientX - rect.left;
      const cy = e.clientY - rect.top;
      const prevScale = scaleRef.current;
      const factor = e.deltaY < 0 ? 1.12 : 1 / 1.12;
      const newScale = Math.min(Math.max(prevScale * factor, 0.5), 8);
      const { x: prevTx, y: prevTy } = translateRef.current;
      const newTx = cx + (prevTx - cx) * (newScale / prevScale);
      const newTy = cy + (prevTy - cy) * (newScale / prevScale);
      applyTransform(newScale, newTx, newTy);
    },
    [applyTransform]
  );

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    container.addEventListener("wheel", handleWheel, { passive: false });
    return () => container.removeEventListener("wheel", handleWheel);
  // imageUrl ensures the effect re-runs once the viewport div is actually in the DOM
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [handleWheel, imageUrl]);

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    dragStartRef.current = {
      mx: e.clientX,
      my: e.clientY,
      tx: translateRef.current.x,
      ty: translateRef.current.y,
    };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!dragStartRef.current) return;
    const { mx, my, tx, ty } = dragStartRef.current;
    applyTransform(scaleRef.current, tx + e.clientX - mx, ty + e.clientY - my);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    dragStartRef.current = null;
  };

  const zoomBy = (factor: number) => {
    const container = containerRef.current;
    const prevScale = scaleRef.current;
    const newScale = Math.min(Math.max(prevScale * factor, 0.5), 8);
    // zoom towards centre of container
    const cx = container ? container.clientWidth / 2 : 0;
    const cy = container ? container.clientHeight / 2 : 0;
    const { x: prevTx, y: prevTy } = translateRef.current;
    applyTransform(
      newScale,
      cx + (prevTx - cx) * (newScale / prevScale),
      cy + (prevTy - cy) * (newScale / prevScale)
    );
  };

  const resetView = () => applyTransform(1, 0, 0);

  // ─────────────────────────────────────────────────────────────────────────

  const handleReupload = async () => {
    if (!onReuploadImage) return;
    setReuploading(true);
    try {
      await onReuploadImage();
    } finally {
      setReuploading(false);
    }
  };

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-gray-300 bg-gray-50 h-96 text-gray-400 text-sm">
        <span>Zdjęcie niedostępne</span>
        {onReuploadImage && (
          <button
            onClick={handleReupload}
            disabled={reuploading}
            className="text-sm px-3 py-1.5 rounded-lg border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            {reuploading ? "Wgrywam…" : "Ponów wgrywanie zdjęcia"}
          </button>
        )}
      </div>
    );
  }

  if (loading || !imageUrl) {
    return (
      <div className="rounded-xl border border-gray-200 overflow-hidden bg-gray-100 h-96 animate-pulse" />
    );
  }

  return (
    <div className="relative rounded-xl border border-gray-200 bg-gray-50">
      {/* Zoom controls */}
      <div className="absolute top-2 right-2 z-10 flex items-center gap-1">
        <button
          onClick={() => zoomBy(1.25)}
          title="Przybliż"
          className="w-7 h-7 flex items-center justify-center rounded-md bg-white/90 border border-gray-300 text-gray-700 hover:bg-gray-100 shadow-sm text-base leading-none"
        >
          +
        </button>
        <button
          onClick={() => zoomBy(1 / 1.25)}
          title="Oddal"
          className="w-7 h-7 flex items-center justify-center rounded-md bg-white/90 border border-gray-300 text-gray-700 hover:bg-gray-100 shadow-sm text-base leading-none"
        >
          −
        </button>
        {(scale !== 1 || translate.x !== 0 || translate.y !== 0) && (
          <button
            onClick={resetView}
            title="Resetuj widok"
            className="h-7 px-2 flex items-center justify-center rounded-md bg-white/90 border border-gray-300 text-gray-600 hover:bg-gray-100 shadow-sm text-xs"
          >
            Reset
          </button>
        )}
      </div>

      {/* Viewport */}
      <div
        ref={containerRef}
        className="overflow-hidden max-h-[70vh] select-none"
        style={{ cursor: isDragging ? "grabbing" : "grab" }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={imageUrl}
          alt={`Receipt ${scanId}`}
          className="w-full object-contain block"
          style={{
            transform: `translate(${translate.x}px, ${translate.y}px) scale(${scale})`,
            transformOrigin: "0 0",
            transition: isDragging ? "none" : "transform 0.08s ease-out",
            willChange: "transform",
          }}
          draggable={false}
          loading="lazy"
          onError={() => {
            // If presigned URL fails (expired / network), try the proxy as last resort.
            const proxyUrl = `/api/receipts/${scanId}/image${refreshKey > 0 ? `?t=${refreshKey}` : ""}`;
            if (imageUrl !== proxyUrl) {
              setImageUrl(proxyUrl);
            } else {
              setError(true);
            }
          }}
        />
      </div>
    </div>
  );
}
