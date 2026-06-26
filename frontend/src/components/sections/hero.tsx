"use client";

import Link from "next/link";
import { motion, useReducedMotion, useScroll, useTransform } from "motion/react";
import { ArrowRight, CreditCard } from "lucide-react";

import { Button } from "@/components/ui/button";
import { WordReveal } from "@/components/ui/motion";
import { HeroFlow } from "@/components/sections/hero-flow";

const EASE = [0.16, 1, 0.3, 1] as const;

/**
 * Cinematic, near-full-height hero. The copy block reveals as a kinetic
 * word-cascade; the whole stage drifts + fades slightly on scroll so leaving
 * the hero feels like a camera move rather than a hard cut.
 */
export function Hero() {
  const reduced = useReducedMotion();
  const { scrollYProgress } = useScroll();
  const y = useTransform(scrollYProgress, [0, 0.18], [0, -60]);
  const opacity = useTransform(scrollYProgress, [0, 0.16], [1, 0]);

  return (
    <section className="relative flex min-h-[92vh] items-center overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-hero-field" />
      <div className="pointer-events-none absolute inset-0 bg-starfield opacity-50" />
      {/* Bottom fade so the hero melts into the next section */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-32 bg-linear-to-t from-background to-transparent" />

      <motion.div
        style={reduced ? undefined : { y, opacity }}
        className="relative mx-auto grid w-full max-w-6xl items-center gap-12 px-6 py-20 lg:grid-cols-[1.1fr_0.9fr] lg:gap-8"
      >
        <div>
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: EASE }}
            className="inline-flex items-center gap-2 rounded-full border border-hairline bg-card/50 px-4 py-1.5 text-xs text-muted-foreground backdrop-blur-sm"
          >
            <CreditCard className="size-3.5 text-gold" />
            Google Maps for Indian credit card rewards
          </motion.div>

          <h1 className="mt-7 font-heading text-5xl leading-[0.95] tracking-tight text-foreground sm:text-7xl">
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
            className="mt-7 max-w-md text-base leading-relaxed text-muted-foreground sm:text-lg"
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
              <Link href="#how">See how it works</Link>
            </Button>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: EASE, delay: 1.1 }}
            className="mt-14 grid max-w-md grid-cols-3 gap-6 border-t border-hairline pt-6"
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
        >
          <HeroFlow />
        </motion.div>
      </motion.div>

      {/* Scroll cue */}
      {!reduced && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.6, duration: 1 }}
          className="pointer-events-none absolute bottom-8 left-1/2 hidden -translate-x-1/2 lg:block"
        >
          <motion.div
            animate={{ y: [0, 8, 0] }}
            transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
            className="flex h-9 w-5 items-start justify-center rounded-full border border-hairline p-1"
          >
            <span className="size-1.5 rounded-full bg-gold" />
          </motion.div>
        </motion.div>
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
