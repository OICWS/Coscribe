import { useEffect, useRef } from "react";

// The effort track at Ultra, matched to Claude Code's: a smooth field from grey at the faster end
// to a muted violet at the smarter end, sweeping in from the right with a ragged edge and then
// holding still; over it a grid of squares, five to the height, each a little lighter than the
// field, so the field itself draws the lines between them and the grid fades with it; and white
// that lights squares at random, in soft waves that keep running from the smarter end to the
// faster one.
const ROWS = 5;
const SWEEP_SECONDS = 1;
// One white wave crosses the track in this time; a second follows half a period behind.
const WAVE_SECONDS = 2.4;
// Measured on the reference: share of the width, then the field's colour there.
const FIELD: readonly [number, string][] = [
  [0, "rgb(226, 225, 232)"],
  [0.25, "rgb(212, 205, 234)"],
  [0.5, "rgb(176, 156, 220)"],
  [0.75, "rgb(158, 134, 210)"],
  [1, "rgb(148, 121, 203)"],
];
// How many squares deep the sweeping edge is: across it each square fades in on its own, so the
// edge is ragged and uneven in shade.
const RAGGED = 3;

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
    const cell = height / ROWS;
    const cols = Math.ceil(width / cell);
    const field = context.createLinearGradient(0, 0, width, 0);
    for (const [at, colour] of FIELD) field.addColorStop(at, colour);
    // Per square, drawn once: how much lighter than the field it is, how many squares ahead of the
    // sweeping edge it starts to fade in, and whether and how brightly a passing wave lights it.
    const squares = Array.from({ length: cols * ROWS }, () => ({
      tint: 0.06 + Math.random() * 0.08,
      lag: Math.random() * RAGGED,
      spark: Math.random(),
      flicker: Math.random() * Math.PI * 2,
    }));
    const start = performance.now();
    let frame = 0;

    const draw = (now: number) => {
      const seconds = (now - start) / 1000;
      const progress = still ? 1 : Math.min(1, seconds / SWEEP_SECONDS);
      // The edge starts right of the track and ends left of it, so every square is whole by then.
      const front = (1 - progress * progress * (3 - 2 * progress)) * (cols + 2 * RAGGED) - RAGGED;
      const waveTime = still ? -1 : seconds - SWEEP_SECONDS;
      const waves =
        waveTime < 0 ? [] : [0, 0.5].map((offset) => 1.15 - ((waveTime / WAVE_SECONDS + offset) % 1) * 1.4);
      context.clearRect(0, 0, width, height);
      context.save();
      context.fillStyle = field;
      if (progress >= 1) context.fillRect(0, 0, width, height);
      for (let col = 0; col < cols; col++) {
        const share = (col + 0.5) / cols;
        const x = col * cell;
        // The grid and the white both fade with the field towards the faster end.
        const weight = Math.min(1, 0.2 + share * 1.1);
        let glow = 0;
        for (const wave of waves) {
          const behind = share - wave;
          glow = Math.max(glow, behind >= 0 ? Math.exp(-behind / 0.25) : Math.exp(behind / 0.02));
        }
        for (let row = 0; row < ROWS; row++) {
          const square = squares[row * cols + col];
          const shown = progress >= 1 ? 1 : Math.min(1, Math.max(0, (col - front + square.lag) / RAGGED));
          if (shown === 0) continue;
          context.globalAlpha = shown;
          if (progress < 1) {
            context.fillStyle = field;
            context.fillRect(x, row * cell, cell, cell);
          }
          const lit = square.spark < 0.32 ? glow : 0;
          const shimmer = 0.85 + 0.15 * Math.sin(seconds * 8 + square.flicker);
          const white = (square.tint + lit * 0.5 * shimmer) * weight;
          context.fillStyle = `rgba(255, 255, 255, ${Math.min(0.7, white)})`;
          context.fillRect(x + 0.5, row * cell + 0.5, cell - 1, cell - 1);
        }
      }
      context.restore();
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
