"use client";

import Link from "next/link";
import {
  motion,
  useReducedMotion,
  useScroll,
  useTransform,
} from "motion/react";
import { ArrowRight, CreditCard } from "lucide-react";

import { Button } from "@/components/ui/button";
import { WordReveal } from "@/components/ui/motion";
import { HeroFlow } from "@/components/sections/hero-flow";

const EASE = [0.16, 1, 0.3, 1] as const;

/**
 * Edge-to-edge cinematic hero. The headline spans the full width at fluid
 * display scale; the strategy-flow card floats to the right edge. The whole
 * stage is pinned-and-released: as you scroll the tall track, the content
 * scales down and fades while the next section rises underneath — an Apple-style
 * "camera pull-back" rather than a hard cut.
 */
export function Hero() {
  const reduced = useReducedMotion();
  // Drive the pin-release off raw document scroll position in PIXELS, not a
  // fraction of the (very tall) page. A scoped useScroll({ target }) mis-reads
  // its progress on first paint before layout is measured, which left the whole
  // hero invisible until the first scroll. scrollY starts at a correct 0 on
  // mount, so the hero is fully crisp/opaque at rest and only pulls back as you
  // scroll the first ~viewport away.
  const { scrollY } = useScroll();
  // px thresholds: hero holds crisp for the first ~12% of the viewport, then
  // scales/fades/blurs out by the time you've scrolled ~70% of it.
  const VH = typeof window !== "undefined" ? window.innerHeight : 800;
  const start = VH * 0.12;
  const end = VH * 0.7;
  const scale = useTransform(scrollY, [start, end], [1, 0.94], { clamp: true });
  const y = useTransform(scrollY, [start, end], [0, -80], { clamp: true });
  const opacity = useTransform(scrollY, [start, end], [1, 0], { clamp: true });
  const blur = useTransform(scrollY, [start, end], [0, 6], { clamp: true });
  const filter = useTransform(blur, (b) => `blur(${b}px)`);

  return (
    <section className="relative flex min-h-[100svh] items-center overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-hero-field" />
      <div className="pointer-events-none absolute inset-0 bg-starfield opacity-50" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-linear-to-t from-background to-transparent" />

      <motion.div
        style={reduced ? undefined : { scale, y, opacity, filter }}
        className="relative grid w-full grid-cols-1 items-center gap-12 px-5 py-24 sm:px-8 lg:grid-cols-[1.15fr_0.85fr] lg:gap-10 lg:px-12 xl:px-16 2xl:px-24"
      >
        <div className="max-w-[46rem]">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: EASE }}
            className="inline-flex items-center gap-2 rounded-full border border-hairline bg-card/50 px-4 py-1.5 text-xs text-muted-foreground backdrop-blur-sm"
          >
            <CreditCard className="size-3.5 text-gold" />
            Google Maps for Indian credit card rewards
          </motion.div>

          <h1 className="mt-8 font-heading font-light leading-[0.92] tracking-tight text-foreground text-[clamp(3rem,8.5vw,8rem)]">
            <WordReveal text="Your cards." delay={0.15} />
            <br />
            <WordReveal text="Your goal." delay={0.3} />
            <br />
            <WordReveal
              text="Mapped."
              delay={0.5}
              wordClassName="italic text-gold"
            />
          </h1>

          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: EASE, delay: 0.8 }}
            className="mt-8 max-w-xl text-base leading-relaxed text-muted-foreground sm:text-lg"
          >
            Tell OptiMiles where you want to fly. It maps the cards already in
            your wallet into a clear, explainable route to get you there, which
            card to use, when to transfer, and exactly when you&apos;ll arrive.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: EASE, delay: 0.95 }}
            className="mt-10 flex flex-wrap items-center gap-3"
          >
            <Button
              asChild
              size="lg"
              className="bg-gold text-gold-foreground hover:bg-gold/90"
            >
              <Link href="/signup">
                Build my card strategy <ArrowRight />
              </Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="ghost"
              className="text-foreground hover:bg-secondary"
            >
              <Link href="#simulate">Try the simulator</Link>
            </Button>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: EASE, delay: 1.1 }}
            className="mt-14 grid max-w-lg grid-cols-3 gap-6 border-t border-hairline pt-6"
          >
            <HeroStat value="8" label="Cards supported" />
            <HeroStat value="0" label="SMS or statements read" />
            <HeroStat value="100%" label="Explainable routing" />
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 30, rotate: 2 }}
          animate={{ opacity: 1, y: 0, rotate: 1 }}
          transition={{ duration: 1, ease: EASE, delay: 0.5 }}
          className="lg:justify-self-end lg:pr-2"
        >
          <HeroFlow />
        </motion.div>
      </motion.div>

      {/* Scroll cue — points straight at the live simulator below */}
      {!reduced && (
        <motion.a
          href="#simulate"
          aria-label="Scroll to the simulator"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.6, duration: 1 }}
          style={{ opacity }}
          className="group absolute bottom-8 left-1/2 hidden -translate-x-1/2 flex-col items-center gap-2 lg:flex"
        >
          <span className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground transition-colors group-hover:text-foreground">
            Try it now
          </span>
          <motion.span
            animate={{ y: [0, 8, 0] }}
            transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
            className="flex h-9 w-5 items-start justify-center rounded-full border border-hairline p-1"
          >
            <span className="size-1.5 rounded-full bg-gold" />
          </motion.span>
        </motion.a>
      )}
    </section>
  );
}

function HeroStat({ value, label }: { value: string; label: string }) {
  return (
    <div>
      <p className="font-heading text-2xl text-foreground sm:text-3xl">
        {value}
      </p>
      <p className="mt-1 text-xs leading-snug text-muted-foreground/80">
        {label}
      </p>
    </div>
  );
}
