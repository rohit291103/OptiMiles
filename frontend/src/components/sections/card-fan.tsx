"use client";

import Image from "next/image";
import {
  motion,
  useMotionTemplate,
  useReducedMotion,
  useScroll,
  useTransform,
  type MotionValue,
} from "motion/react";
import * as React from "react";

/**
 * Fan geometry. Everything about the choreography is a constant here — tune
 * these, not the JSX. Values were dialed against a 3-turn scroll on a 1440px
 * viewport; the card size is fluid so the fan holds its shape down to mobile.
 */
const SPREAD_DEG = 40; // angular gap between neighbouring cards
const PIVOT = "50% 190%"; // rotation origin *below* the card => hand-of-cards fan
const PERSPECTIVE = 1600; // px, on the stage
const STAGE_TILT = 14; // rotateX on the whole fan, so it reads as tilted in space
const SPIN_DEG = 200; // extra whole-fan rotation over the back half of the scroll
const STAGGER = 0.035; // per-card offset, in scroll-progress units
const FAN_DURATION = 0.34; // progress span each card takes to reach its fan slot

/** Normalized to 1400x883 (ISO/IEC 7810 ID-1) with transparent rounded corners. */
const CARDS = [
  { src: "/cards/fan/hdfc-infinia.png", name: "HDFC Infinia" },
  { src: "/cards/fan/axis-atlas.png", name: "Axis Atlas" },
  { src: "/cards/fan/hdfc-diners-black.png", name: "HDFC Diners Club Black" },
  { src: "/cards/fan/amex-platinum-travel.png", name: "Amex Platinum Travel" },
  { src: "/cards/fan/hdfc-regalia-gold.png", name: "HDFC Regalia Gold" },
  { src: "/cards/fan/hsbc-travelone.png", name: "HSBC TravelOne" },
  { src: "/cards/fan/axis-magnus.png", name: "Axis Magnus" },
  { src: "/cards/fan/amex-platinum-charge.png", name: "Amex Platinum Charge" },
];

/**
 * CardFan: the signature scroll scene. A tall track pins a stage; as you scroll,
 * the wallet unfolds from a tight stack into a full radial fan, then the whole
 * fan rotates as one body.
 *
 * Position is a pure function of scroll progress — no entrance animations — so
 * scrolling back up exactly reverses the fan. Transform + opacity only, which
 * keeps the whole scene on the compositor.
 */
export function CardFan() {
  const ref = React.useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end end"],
  });

  // Copy holds the stage while the cards are still stacked, then clears out so
  // the fan owns the frame.
  const headOpacity = useTransform(scrollYProgress, [0, 0.16, 0.3], [1, 1, 0]);
  const headY = useTransform(scrollYProgress, [0, 0.3], [0, -40]);
  const tailOpacity = useTransform(
    scrollYProgress,
    [0.62, 0.78, 0.96, 1],
    [0, 1, 1, 0],
  );
  const glow = useTransform(scrollYProgress, [0, 0.5], [0.35, 1]);

  return (
    <div ref={ref} className="relative h-[300vh]">
      <div className="sticky top-0 flex h-screen items-center justify-center overflow-hidden">
        {/* Gold field that blooms as the fan opens */}
        <motion.div
          style={reduced ? undefined : { opacity: glow }}
          className="pointer-events-none absolute inset-0 bg-aurora"
        />
        <div className="pointer-events-none absolute inset-0 bg-starfield opacity-40" />

        {/* Opening copy — sits behind the fan */}
        <motion.div
          style={reduced ? undefined : { opacity: headOpacity, y: headY }}
          className="pointer-events-none absolute inset-x-0 top-[18vh] z-0 px-6 text-center"
        >
          <p className="text-xs uppercase tracking-[0.22em] text-gold">
            The wallet you already have
          </p>
          <h2 className="mx-auto mt-4 max-w-4xl font-heading text-4xl leading-[1.05] tracking-tight text-foreground sm:text-6xl lg:text-7xl">
            Eight cards.{" "}
            <span className="italic text-gold">One route.</span>
          </h2>
        </motion.div>

        {/* The stage */}
        <div
          style={{ perspective: `${PERSPECTIVE}px` }}
          className="relative z-10 h-full w-full"
        >
          <motion.div
            style={{
              rotateX: reduced ? 0 : STAGE_TILT,
              transformStyle: "preserve-3d",
            }}
            className="relative h-full w-full"
          >
            {CARDS.map((card, i) => (
              <FanCard
                key={card.src}
                card={card}
                index={i}
                count={CARDS.length}
                progress={scrollYProgress}
                reduced={!!reduced}
              />
            ))}
          </motion.div>
        </div>

        {/* Closing copy — arrives once the fan is open */}
        <motion.div
          style={reduced ? undefined : { opacity: tailOpacity }}
          className="pointer-events-none absolute inset-x-0 bottom-[12vh] z-20 px-6 text-center"
        >
          <p className="mx-auto max-w-xl text-base leading-relaxed text-muted-foreground sm:text-lg">
            OptiMiles maps every rupee of spend across all of them — then tells
            you which card to swipe, when to transfer, and exactly when you fly.
          </p>
        </motion.div>
      </div>
    </div>
  );
}

function FanCard({
  card,
  index,
  count,
  progress,
  reduced,
}: {
  card: (typeof CARDS)[number];
  index: number;
  count: number;
  progress: MotionValue<number>;
  reduced: boolean;
}) {
  // Fan slot: cards spread symmetrically about the vertical axis.
  const slot = (index - (count - 1) / 2) * SPREAD_DEG;

  // Each card leaves the stack slightly after the one before it, so the fan
  // unfurls rather than snapping open.
  const start = 0.06 + index * STAGGER;
  const open = start + FAN_DURATION;

  const rotate = useTransform(
    progress,
    [start, open, 1],
    [0, slot, slot + SPIN_DEG],
  );
  const scale = useTransform(progress, [start, open, 1], [0.86, 1, 0.92]);
  const opacity = useTransform(progress, [0, start], [0.55, 1]);

  // Specular sweep: the highlight angle is derived from the card's own rotation
  // so the light stays fixed in the world while the card turns under it. This
  // is what sells the 3D — without it the fan reads as flat stickers.
  const sheenAngle = useTransform(rotate, (r) => 110 - r);
  const sheen = useMotionTemplate`linear-gradient(${sheenAngle}deg, transparent 34%, rgba(255,255,255,0.18) 49%, transparent 64%)`;

  const staticStyle = { rotate: slot, transformOrigin: PIVOT };

  return (
    <motion.div
      style={
        reduced
          ? staticStyle
          : { rotate, scale, opacity, transformOrigin: PIVOT }
      }
      className="absolute left-1/2 top-1/2 w-[clamp(190px,25vw,360px)] -translate-x-1/2 -translate-y-1/2"
    >
      <div className="relative aspect-[1.586/1] w-full drop-shadow-[0_28px_45px_rgba(0,0,0,0.55)]">
        <Image
          src={card.src}
          alt={card.name}
          fill
          sizes="(max-width: 640px) 55vw, (max-width: 1024px) 34vw, 24vw"
          className="rounded-[6%] object-contain"
          priority={index < 3}
        />
        {/* specular sweep */}
        <motion.div
          aria-hidden
          style={reduced ? undefined : { backgroundImage: sheen }}
          className="pointer-events-none absolute inset-0 rounded-[6%] mix-blend-overlay"
        />
      </div>
    </motion.div>
  );
}
