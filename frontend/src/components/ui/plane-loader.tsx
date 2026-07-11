"use client";

import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "motion/react";

import { cn } from "@/lib/utils";

/**
 * The branded "we're building your strategy" animation — a plane tracing a
 * dotted flight arc while the loading copy cycles through the actual pipeline
 * stages. Used wherever the user waits on the engine (strategy generation) so
 * the wait feels like the product working, not a frozen screen.
 *
 * Honors prefers-reduced-motion: renders the arc statically with a steady
 * status line instead of animating.
 */

const EASE = [0.16, 1, 0.3, 1] as const;

// Reads as the engine narrating its own work — matches the real 11-stage
// pipeline (intent → charts → opportunities → simulate → rank → narrate).
const DEFAULT_STAGES = [
  "Reading your goal and route…",
  "Pulling verified award charts…",
  "Scoring every card in your wallet…",
  "Routing your spend for maximum miles…",
  "Simulating month-by-month accumulation…",
  "Writing your strategy…",
];

export function PlaneLoader({
  stages = DEFAULT_STAGES,
  className,
}: {
  stages?: string[];
  className?: string;
}) {
  const reduced = useReducedMotion();
  const [stage, setStage] = useState(0);

  // Advance the status line on a gentle cadence, holding on the last one until
  // the real work finishes (the parent unmounts us when the result lands).
  useEffect(() => {
    if (reduced) return;
    const id = setInterval(() => {
      setStage((s) => Math.min(s + 1, stages.length - 1));
    }, 1400);
    return () => clearInterval(id);
  }, [reduced, stages.length]);

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-6 py-10 text-center",
        className,
      )}
      role="status"
      aria-live="polite"
    >
      <FlightArc animate={!reduced} />
      <p className="min-h-5 text-sm text-muted-foreground transition-opacity">
        {reduced ? "Building your strategy…" : stages[stage]}
      </p>
    </div>
  );
}

/**
 * A dotted great-circle arc with an origin/destination pin and a plane that
 * flies along it on a loop, leaving a gold trail behind. Pure SVG so it stays
 * crisp and self-contained (no external assets, CSP-safe).
 */
function FlightArc({ animate }: { animate: boolean }) {
  // Arc from (16,72) up to (224,40): a quadratic curve peaking mid-span.
  const path = "M16 72 Q120 -8 224 40";

  return (
    <svg
      viewBox="0 0 240 88"
      className="h-20 w-56 overflow-visible"
      aria-hidden="true"
    >
      {/* Static dotted route the plane follows. */}
      <path
        d={path}
        fill="none"
        stroke="var(--gold)"
        strokeOpacity="0.28"
        strokeWidth="1.5"
        strokeDasharray="2 6"
        strokeLinecap="round"
      />

      {/* The trail the plane draws as it flies — a growing/receding dash. */}
      {animate && (
        <motion.path
          d={path}
          fill="none"
          stroke="var(--gold)"
          strokeWidth="2"
          strokeLinecap="round"
          pathLength={1}
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: [0, 1, 1], opacity: [0, 1, 0] }}
          transition={{
            duration: 2.8,
            ease: EASE,
            repeat: Infinity,
            repeatDelay: 0.2,
          }}
        />
      )}

      {/* Origin + destination pins. */}
      <circle cx="16" cy="72" r="3.5" fill="var(--gold)" />
      <circle cx="224" cy="40" r="3.5" fill="var(--gold)" />
      <circle
        cx="224"
        cy="40"
        r="3.5"
        fill="none"
        stroke="var(--gold)"
        strokeOpacity="0.4"
      >
        {animate && (
          <animate
            attributeName="r"
            values="3.5;9;3.5"
            dur="2.8s"
            repeatCount="indefinite"
          />
        )}
      </circle>

      {/* The plane, riding the same path via offset-path. */}
      {animate ? (
        <motion.g
          initial={{ offsetDistance: "0%", opacity: 0 }}
          animate={{
            offsetDistance: ["0%", "100%"],
            opacity: [0, 1, 1, 0],
          }}
          transition={{
            duration: 2.8,
            ease: EASE,
            repeat: Infinity,
            repeatDelay: 0.2,
          }}
          style={{ offsetPath: `path("${path}")`, offsetRotate: "auto" }}
        >
          <PlaneMark />
        </motion.g>
      ) : (
        <g transform="translate(120 24)">
          <PlaneMark />
        </g>
      )}
    </svg>
  );
}

/** A small gold paper-plane glyph, centered on the origin so it rides the
 * offset-path cleanly (no nested <svg> — this is a bare path in the parent). */
function PlaneMark() {
  return (
    <path
      d="M11 -5 L-9 2.5 L-2.5 4 L-1 9.5 L1.5 5 L9.5 6 Z"
      fill="var(--gold)"
      stroke="var(--gold)"
      strokeWidth="0.5"
      strokeLinejoin="round"
    />
  );
}
