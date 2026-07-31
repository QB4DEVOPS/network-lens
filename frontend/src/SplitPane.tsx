import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

const STORAGE_KEY = "network-lens-split-ratio";
const MIN_PANE_PX = 120;

function minPaneRatio(width: number): number {
  if (width <= 0) return 0.2;
  const minPx = Math.min(MIN_PANE_PX, Math.max(72, width * 0.12));
  return minPx / width;
}

interface SplitPaneProps {
  left: ReactNode;
  right: ReactNode;
  defaultRatio?: number;
}

export function SplitPane({ left, right, defaultRatio = 0.5 }: SplitPaneProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [ratio, setRatio] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const n = parseFloat(saved);
      if (!Number.isNaN(n) && n > 0.15 && n < 0.85) return n;
    }
    return defaultRatio;
  });
  const dragging = useRef(false);
  const ratioRef = useRef(ratio);
  ratioRef.current = ratio;

  const clampRatio = useCallback((next: number, width: number) => {
    const minRatio = minPaneRatio(width);
    const maxRatio = 1 - minRatio;
    return Math.min(maxRatio, Math.max(minRatio, next));
  }, []);

  const applyPointerX = useCallback(
    (clientX: number) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const next = clampRatio((clientX - rect.left) / rect.width, rect.width);
      setRatio(next);
    },
    [clampRatio],
  );

  const stopDragging = useCallback(() => {
    if (!dragging.current) return;
    dragging.current = false;
    document.body.classList.remove("split-dragging");
    localStorage.setItem(STORAGE_KEY, String(ratioRef.current));
  }, []);

  const onDividerPointerDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      e.preventDefault();
      dragging.current = true;
      document.body.classList.add("split-dragging");
      applyPointerX(e.clientX);
      e.currentTarget.setPointerCapture(e.pointerId);
    },
    [applyPointerX],
  );

  const onDividerPointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!dragging.current) return;
      e.preventDefault();
      applyPointerX(e.clientX);
    },
    [applyPointerX],
  );

  const onDividerPointerUp = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!dragging.current) return;
      e.currentTarget.releasePointerCapture(e.pointerId);
      stopDragging();
    },
    [stopDragging],
  );

  useEffect(() => {
    const onWindowPointerMove = (e: PointerEvent) => {
      if (!dragging.current) return;
      e.preventDefault();
      applyPointerX(e.clientX);
    };
    const onWindowPointerUp = () => stopDragging();

    window.addEventListener("pointermove", onWindowPointerMove);
    window.addEventListener("pointerup", onWindowPointerUp);
    window.addEventListener("pointercancel", onWindowPointerUp);
    return () => {
      window.removeEventListener("pointermove", onWindowPointerMove);
      window.removeEventListener("pointerup", onWindowPointerUp);
      window.removeEventListener("pointercancel", onWindowPointerUp);
    };
  }, [applyPointerX, stopDragging]);

  useEffect(() => {
    const onResize = () => {
      if (!containerRef.current) return;
      const width = containerRef.current.getBoundingClientRect().width;
      setRatio((r) => clampRatio(r, width));
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [clampRatio]);

  const leftGrow = ratio;
  const rightGrow = 1 - ratio;

  return (
    <div className="split-pane" ref={containerRef}>
      <div
        className="split-pane-left"
        style={{ flex: `${leftGrow} ${leftGrow} 0`, minWidth: 0 }}
      >
        {left}
      </div>
      <div
        className="split-divider"
        role="separator"
        aria-orientation="vertical"
        aria-valuenow={Math.round(ratio * 100)}
        aria-label="Resize CLI and nac.yaml panes"
        title="Drag to resize panes"
        onPointerDown={onDividerPointerDown}
        onPointerMove={onDividerPointerMove}
        onPointerUp={onDividerPointerUp}
        onPointerCancel={onDividerPointerUp}
        onLostPointerCapture={stopDragging}
      />
      <div
        className="split-pane-right"
        style={{ flex: `${rightGrow} ${rightGrow} 0`, minWidth: 0 }}
      >
        {right}
      </div>
    </div>
  );
}
