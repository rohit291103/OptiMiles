"use client";

import * as React from "react";
import {
  motion,
  useReducedMotion,
  useScroll,
  useTransform,
  type Variants,
  type MotionProps,
} from "motion/react";

import { cn } from "@/lib/utils";

/**
 * Shared easing + timing so every section animates with the same hand.
 * A long, soft cubic-bezier reads "premium" rather than "bouncy".
 */
const EASE = [0.16, 1, 0.3, 1] as const;

/**
 * FadeUp: the workhorse scroll-reveal. Fades + lifts an element into place the
 * first time it enters the viewport. Honors prefers-reduced-motion (renders
 * static). `delay` staggers siblings; `as` swaps the element.
 */
export function FadeUp({
  children,
  className,
  delay = 0,
  y = 28,
  once = true,
  amount = 0.3,
  as = "div",
  ...props
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  y?: number;
  once?: boolean;
  amount?: number;
  as?: keyof typeof motion;
} & MotionProps) {
  const reduced = useReducedMotion();
  const Comp = motion[as] as typeof motion.div;

  if (reduced) {
    return (
      <Comp className={className} {...props}>
        {children}
      </Comp>
    );
  }

  return (
    <Comp
      className={className}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once, amount }}
      transition={{ duration: 0.8, ease: EASE, delay }}
      {...props}
    >
      {children}
    </Comp>
  );
}

/**
 * Stagger: a container that reveals its direct <StaggerItem> children in a
 * waterfall as it scrolls into view.
 */
const staggerParent: Variants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.09, delayChildren: 0.05 },
  },
};

const staggerChild: Variants = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.7, ease: EASE } },
};

export function Stagger({
  children,
  className,
  amount = 0.25,
  once = true,
  as = "div",
  ...props
}: {
  children: React.ReactNode;
  className?: string;
  amount?: number;
  once?: boolean;
  as?: keyof typeof motion;
} & MotionProps) {
  const reduced = useReducedMotion();
  const Comp = motion[as] as typeof motion.div;

  if (reduced) {
    return (
      <Comp className={className} {...props}>
        {children}
      </Comp>
    );
  }

  return (
    <Comp
      className={className}
      variants={staggerParent}
      initial="hidden"
      whileInView="show"
      viewport={{ once, amount }}
      {...props}
    >
      {children}
    </Comp>
  );
}

export function StaggerItem({
  children,
  className,
  as = "div",
  ...props
}: {
  children: React.ReactNode;
  className?: string;
  as?: keyof typeof motion;
} & MotionProps) {
  const reduced = useReducedMotion();
  const Comp = motion[as] as typeof motion.div;

  if (reduced) {
    return (
      <Comp className={className} {...props}>
        {children}
      </Comp>
    );
  }

  return (
    <Comp className={className} variants={staggerChild} {...props}>
      {children}
    </Comp>
  );
}

/**
 * Parallax: translates a layer on the Y axis as it scrolls through the
 * viewport. `speed` > 0 drifts slower than scroll (moves up), giving depth.
 */
export function Parallax({
  children,
  className,
  speed = 60,
}: {
  children: React.ReactNode;
  className?: string;
  speed?: number;
}) {
  const ref = React.useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"],
  });
  const y = useTransform(scrollYProgress, [0, 1], [speed, -speed]);

  return (
    <div ref={ref} className={cn("relative", className)}>
      <motion.div style={reduced ? undefined : { y }}>{children}</motion.div>
    </div>
  );
}

/**
 * WordReveal: splits a string into words and reveals them in a soft upward
 * cascade — the signature "kinetic headline" entrance. Each word is masked by
 * its overflow-hidden wrapper so it slides up from below the line.
 */
export function WordReveal({
  text,
  className,
  wordClassName,
  delay = 0,
}: {
  text: string;
  className?: string;
  wordClassName?: string;
  delay?: number;
}) {
  const reduced = useReducedMotion();
  const words = text.split(" ");

  if (reduced) {
    return <span className={className}>{text}</span>;
  }

  return (
    <motion.span
      className={cn("inline", className)}
      initial="hidden"
      animate="show"
      variants={{
        hidden: {},
        show: { transition: { staggerChildren: 0.08, delayChildren: delay } },
      }}
    >
      {words.map((word, i) => (
        <span
          key={`${word}-${i}`}
          className="inline-block -mb-[0.18em] overflow-hidden align-bottom"
        >
          <motion.span
            className={cn("inline-block pb-[0.18em]", wordClassName)}
            variants={{
              hidden: { y: "110%" },
              show: { y: 0, transition: { duration: 0.9, ease: EASE } },
            }}
          >
            {word}
            {i < words.length - 1 ? " " : ""}
          </motion.span>
        </span>
      ))}
    </motion.span>
  );
}
