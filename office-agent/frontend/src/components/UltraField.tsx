import { useEffect, useRef } from "react";

// The effort track at Ultra: a mosaic of small squares, sparse and pale at the faster end and
// dense violet at the smarter end, that sweeps in from the right and then keeps twinkling.
const CELL = 3;
const SWEEP_SECONDS = 1;
const PALE = [205, 192, 247];
const DEEP = [112, 76, 224];

export function UltraField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return;
    const still = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    const { width, height } = canvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    context.scale(ratio, ratio);
    const cols = Math.ceil(width / CELL);
    const rows = Math.ceil(height / CELL);
    // Per square, drawn once so the pattern holds still while it twinkles: when it lights up
    // (threshold), when it pulses (phase), and how deep its violet is (tint).
    const squares = Array.from({ length: cols * rows }, () => ({
      threshold: Math.random(),
      phase: Math.random() * Math.PI * 2,
      tint: Math.random(),
    }));
    const start = performance.now();
    let frame = 0;

    const draw = (now: number) => {
      const seconds = (now - start) / 1000;
      const progress = still ? 1 : Math.min(1, seconds / SWEEP_SECONDS);
      // Where the mosaic begins, as a share of the width: from the right edge to the left one,
      // slow at both ends.
      const front = 1 - progress * progress * (3 - 2 * progress);
      context.clearRect(0, 0, width, height);
      for (let col = 0; col < cols; col++) {
        const share = (col + 0.5) / cols;
        if (share < front) continue;
        const edge = Math.min(1, (share - front) / 0.12);
        const density = Math.max(0, (share - 0.04) / 0.96) ** 1.3 * edge;
        for (let row = 0; row < rows; row++) {
          const square = squares[row * cols + col];
          const twinkle = still ? 0 : Math.sin(seconds * 2.4 + square.phase) * 0.18;
          const alpha = Math.min(1, density * 1.15 - square.threshold * 0.55 + twinkle);
          if (alpha < 0.05) continue;
          const depth = Math.min(1, Math.max(0, density * 0.85 + square.tint * 0.3 - 0.1));
          const [r, g, b] = PALE.map((pale, i) => Math.round(pale + (DEEP[i] - pale) * depth));
          context.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`;
          context.fillRect(col * CELL, row * CELL, CELL - 0.5, CELL - 0.5);
        }
      }
      if (!still) frame = requestAnimationFrame(draw);
    };
    frame = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(frame);
  }, []);

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden rounded-lg" aria-hidden>
      <canvas ref={canvasRef} data-testid="effort-ultra-field" className="h-full w-full" />
    </div>
  );
}
