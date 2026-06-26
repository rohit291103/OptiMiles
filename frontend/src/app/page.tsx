import Link from "next/link";
import { ArrowRight, CreditCard, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Reveal } from "@/components/ui/reveal";
import { GoalSimulator } from "@/components/goal-simulator";
import { SiteNav } from "@/components/site-nav";
import { SiteFooter } from "@/components/site-footer";
import { HeroFlow } from "@/components/sections/hero-flow";
import { DreamOutcomes } from "@/components/sections/dream-outcomes";
import { HowItWorks } from "@/components/sections/how-it-works";
import { TrustPillars } from "@/components/sections/trust-pillars";
import { StrategyOutput } from "@/components/sections/strategy-output";
import { SupportedCards } from "@/components/sections/supported-cards";
import { EcosystemMarquee } from "@/components/sections/ecosystem-marquee";
import { BuiltFor } from "@/components/sections/built-for";
import { FeatureTabs } from "@/components/sections/feature-tabs";
import { Faq } from "@/components/sections/faq";

export default function Home() {
  return (
    <div className="bg-grain min-h-screen">
      <SiteNav />

      <main>
        {/* Hero */}
        <section className="relative overflow-hidden">
          <div className="pointer-events-none absolute inset-0 bg-hero-field" />
          <div className="pointer-events-none absolute inset-0 bg-starfield opacity-50" />
          <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-6 pt-24 pb-24 sm:pt-32 lg:grid-cols-[1.1fr_0.9fr] lg:gap-8">
            <div>
              <Reveal className="inline-flex items-center gap-2 rounded-full border border-hairline bg-card/50 px-4 py-1.5 text-xs text-muted-foreground backdrop-blur-sm">
                <CreditCard className="size-3.5 text-gold" />
                Credit card strategy, not a rewards blog
              </Reveal>
              <Reveal
                as="h1"
                delay={80}
                className="text-balance mt-7 max-w-xl font-heading text-5xl leading-[0.98] tracking-tight text-foreground sm:text-7xl"
              >
                Which card
                <br />
                to swipe.
                <br />
                <span className="italic text-gold">Every time.</span>
              </Reveal>
              <Reveal
                as="p"
                delay={160}
                className="mt-7 max-w-md text-base leading-relaxed text-muted-foreground sm:text-lg"
              >
                OptiMiles tells you which credit card to use for every
                purchase, so the miles and points you&apos;re already earning
                add up to a real trip, not a forgotten statement credit.
              </Reveal>
              <Reveal
                delay={240}
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
              </Reveal>

              <Reveal
                delay={320}
                className="mt-14 grid max-w-md grid-cols-3 gap-6 border-t border-hairline pt-6"
              >
                <HeroStat value="8" label="Cards supported" />
                <HeroStat value="0" label="SMS or statements read" />
                <HeroStat value="100%" label="Explainable routing" />
              </Reveal>
            </div>

            <HeroFlow />
          </div>
        </section>

        {/* Dream outcomes */}
        <section className="mx-auto max-w-6xl px-6 pb-20">
          <SectionHeading
            eyebrow="Where your card spend goes"
            title="Real trips,"
            accent="not just points."
            description="OptiMiles optimizes your credit card spend for goals achieved: the trip, the suite, the lounge, not points earned for their own sake."
          />
          <div className="mt-12">
            <DreamOutcomes />
          </div>
        </section>

        {/* How it works */}
        <section id="how" className="scroll-mt-24 border-y border-hairline bg-card/20 py-20">
          <div className="mx-auto max-w-6xl px-6">
            <SectionHeading
              eyebrow="How it works"
              title="Four steps from credit card spend"
              accent="to redemption."
              description="Goal first, then a card-by-card strategy. You stay in control the whole way."
            />
            <div className="mt-14">
              <HowItWorks />
            </div>
          </div>
        </section>

        {/* Why trust OptiMiles */}
        <section className="mx-auto max-w-6xl px-6 py-20">
          <SectionHeading
            eyebrow="Why trust OptiMiles"
            title="Structured card logic first."
            accent="AI orchestration second."
            description="Every card recommendation traces back to deterministic logic, not a language model improvising transfer ratios."
          />
          <div className="mt-12">
            <TrustPillars />
          </div>
        </section>

        {/* Goal simulator */}
        <section id="simulate" className="scroll-mt-24 border-y border-hairline bg-card/20 py-20">
          <div className="mx-auto max-w-6xl px-6">
            <SectionHeading
              eyebrow="Try it now"
              title="Pick your cards."
              accent="See the path."
              description="Pick a destination, a cabin, and the credit cards you carry, and watch your timeline resolve."
            />
            <div className="mt-12">
              <GoalSimulator />
            </div>
          </div>
        </section>

        {/* Example strategy output */}
        <section className="mx-auto max-w-6xl px-6 py-20">
          <SectionHeading
            eyebrow="What you actually get"
            title="A card strategy you can"
            accent="act on."
            description="Not a score or a vague tip. A concrete plan: which credit card for which spend, the transfer path, and a dated timeline."
          />
          <div className="mt-12">
            <StrategyOutput />
          </div>
        </section>

        {/* Supported cards */}
        <section id="cards" className="scroll-mt-24 border-y border-hairline bg-card/20 py-20">
          <div className="mx-auto max-w-6xl px-6">
            <SectionHeading
              eyebrow="Your existing wallet"
              title="The credit cards you already"
              accent="carry."
              description="OptiMiles maximizes the credit cards you already own before it ever recommends a new one."
            />
            <div className="mt-12">
              <SupportedCards />
            </div>
          </div>
        </section>

        {/* Supported reward ecosystems */}
        <section className="mx-auto max-w-6xl px-6 py-20">
          <SectionHeading
            eyebrow="Supported ecosystems"
            title="Airlines, hotels,"
            accent="and your banks."
            description="Reward currencies and transfer partners across the programs that matter for Indian travel cards."
          />
          <div className="mt-12">
            <EcosystemMarquee />
          </div>
        </section>

        {/* Built for */}
        <section className="mx-auto max-w-6xl px-6 py-20">
          <SectionHeading
            eyebrow="Built for"
            title="However you think"
            accent="about rewards."
          />
          <div className="mt-12">
            <BuiltFor />
          </div>
        </section>

        {/* Capabilities (feature tabs) */}
        <section id="features" className="scroll-mt-24 border-y border-hairline bg-card/20 py-20">
          <div className="mx-auto max-w-6xl px-6">
            <SectionHeading
              eyebrow="Under the hood"
              title="One engine,"
              accent="four sharp tools."
              description="Outcomes come first, but if you want to look closer, here's what's doing the work."
            />
            <div className="mt-12">
              <FeatureTabs />
            </div>
          </div>
        </section>

        {/* Why OptiMiles exists */}
        <section className="mx-auto max-w-3xl px-6 py-24 text-center">
          <Reveal>
            <p className="text-xs uppercase tracking-[0.22em] text-gold">
              Why OptiMiles exists
            </p>
            <p className="mt-6 font-heading text-2xl leading-snug text-foreground sm:text-3xl">
              The seat you want already exists in the credit cards you already carry.
            </p>
            <p className="mt-5 text-base leading-relaxed text-muted-foreground">
              Most people leave business class on the table, not because they
              have the wrong cards, but because no one ever told them which
              card to swipe for which purchase. OptiMiles closes that gap:
              every rupee mapped to a card, every transfer partner understood,
              every redemption a clear, provable path away.
            </p>
          </Reveal>
        </section>

        <Separator className="bg-hairline" />

        {/* FAQ */}
        <section id="faq" className="mx-auto max-w-3xl scroll-mt-24 px-6 py-20">
          <SectionHeading eyebrow="FAQ" title="Questions," accent="answered." />
          <div className="mt-10">
            <Faq />
          </div>
        </section>

        {/* Final CTA */}
        <section className="mx-auto max-w-6xl px-6 pb-24">
          <div className="relative overflow-hidden rounded-3xl border border-hairline bg-card/40 px-8 py-16 text-center backdrop-blur-sm sm:px-16">
            <div className="pointer-events-none absolute inset-0 bg-aurora" />
            <div className="relative">
              <ShieldCheck className="mx-auto size-10 text-gold" />
              <h2 className="mx-auto mt-6 max-w-2xl font-heading text-3xl text-foreground sm:text-4xl">
                Your next redemption is a card strategy away.
              </h2>
              <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
                Create a free account and let OptiMiles chart the most efficient
                path from your credit card spending to your travel goal.
              </p>
              <div className="mt-8 flex flex-wrap justify-center gap-3">
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
                  variant="outline"
                  className="border-hairline"
                >
                  <Link href="#simulate">Explore the simulator</Link>
                </Button>
              </div>
            </div>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
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

function SectionHeading({
  eyebrow,
  title,
  accent,
  description,
}: {
  eyebrow: string;
  title: string;
  accent?: string;
  description?: string;
}) {
  return (
    <Reveal className="max-w-2xl">
      <p className="text-xs uppercase tracking-[0.22em] text-gold">{eyebrow}</p>
      <h2 className="mt-4 font-heading text-3xl text-foreground sm:text-4xl">
        {title} {accent && <span className="italic text-gold">{accent}</span>}
      </h2>
      {description && (
        <p className="mt-4 text-muted-foreground">{description}</p>
      )}
    </Reveal>
  );
}
