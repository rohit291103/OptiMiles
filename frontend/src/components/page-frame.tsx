"use client";

import { motion, useReducedMotion } from "motion/react";

/**
 * Fixed decorative frame that lives behind all page content. Two faint vertical
 * rails sit at the edges of the central content column (max-w-6xl == 72rem),
 * with gold accent nodes and soft ambient glows drifting in the side gutters.
 * Purely decorative and pointer-events-none, so it never affects layout or
 * interaction. Rails fade in on mount; glows breathe unless reduced-motion.
 *
 * Only shown on xl+ where the gutters are actually wide enough to feel empty.
 */
export function PageFrame() {
  const reduced = useReducedMotion();

  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 z-40 hidden xl:block"
    >
      {/* Centered box matching the content column; rails hang off its edges. */}
      <div className="mx-auto h-full w-full max-w-304 px-6">
        <div className="relative h-full">
          {/* Left rail */}
          <Rail side="left" reduced={reduced} />
          {/* Right rail */}
          <Rail side="right" reduced={reduced} />
        </div>
      </div>

      {/* Ambient gutter glows */}
      <motion.div
        className="absolute -left-32 top-1/4 size-144 rounded-full bg-gold/5 blur-3xl"
        animate={reduced ? undefined : { opacity: [0.5, 0.9, 0.5] }}
        transition={{ duration: 9, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute -right-40 top-2/3 size-160 rounded-full bg-gold/4 blur-3xl"
        animate={reduced ? undefined : { opacity: [0.4, 0.75, 0.4] }}
        transition={{
          duration: 11,
          repeat: Infinity,
          ease: "easeInOut",
          delay: 2,
        }}
      />
    </div>
  );
}

function Rail({
  side,
  reduced,
}: {
  side: "left" | "right";
  reduced: boolean | null;
}) {
  const pos = side === "left" ? "left-0" : "right-0";

  return (
    <motion.div
      className={`absolute ${pos} top-0 h-full w-px`}
      initial={reduced ? undefined : { opacity: 0 }}
      animate={reduced ? undefined : { opacity: 1 }}
      transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1], delay: 0.4 }}
    >
      {/* The line itself: fades in at top, solid through the middle, out at base */}
      <div className="h-full w-px bg-linear-to-b from-transparent via-hairline to-transparent" />

      {/* Gold accent nodes that travel down the rail */}
      {!reduced && (
        <>
          <TravelNode delay={0} />
          <TravelNode delay={3.5} />
        </>
      )}

      {/* Static node markers at thirds for an editorial-grid feel */}
      <span className="absolute left-1/2 top-1/3 size-1 -translate-x-1/2 rounded-full bg-gold/40" />
      <span className="absolute left-1/2 top-2/3 size-1 -translate-x-1/2 rounded-full bg-gold/30" />
    </motion.div>
  );
}

/** A small gold dot that drifts down the rail on a slow loop. */
function TravelNode({ delay }: { delay: number }) {
  return (
    <motion.span
      className="absolute left-1/2 size-1.5 -translate-x-1/2 rounded-full bg-gold shadow-[0_0_8px_2px_var(--gold)]"
      initial={{ top: "-2%", opacity: 0 }}
      animate={{
        top: ["-2%", "102%"],
        opacity: [0, 1, 1, 0],
      }}
      transition={{
        duration: 7,
        repeat: Infinity,
        ease: "linear",
        delay,
        times: [0, 0.08, 0.92, 1],
      }}
    />
  );
}
