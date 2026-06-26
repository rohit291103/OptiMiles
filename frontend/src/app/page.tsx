import Link from "next/link";
import { ArrowRight, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { FadeUp } from "@/components/ui/motion";
import { GoalSimulator } from "@/components/goal-simulator";
import { SiteNav } from "@/components/site-nav";
import { SiteFooter } from "@/components/site-footer";
import { Hero } from "@/components/sections/hero";
import { Bleed, Inner } from "@/components/sections/section-shell";
import { SimulatorScene } from "@/components/sections/simulator-scene";
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
    <div className="bg-grain relative min-h-screen">
      <SiteNav />

      <main>
        <Hero />

        {/*
          The product first, Apple-style. The simulator is a pinned scene: the
          intro copy holds the viewport while the live simulator scales/fades up
          into place. Usable on the first scroll — not buried mid-page.
        */}
        <SimulatorScene>
          <GoalSimulator />
        </SimulatorScene>

        {/* Dream outcomes */}
        <Bleed className="py-32">
          <Inner>
            <SectionHeading
              eyebrow="Where your card spend goes"
              title="Real trips,"
              accent="not just points."
              description="OptiMiles optimizes your credit card spend for goals achieved: the trip, the suite, the lounge, not points earned for their own sake."
            />
            <div className="mt-16">
              <DreamOutcomes />
            </div>
          </Inner>
        </Bleed>

        {/* How it works */}
        <Bleed id="how" banded>
          <HowItWorks />
        </Bleed>

        {/* Why trust OptiMiles */}
        <Bleed className="py-32">
          <Inner>
            <SectionHeading
              eyebrow="Why trust OptiMiles"
              title="Structured card logic first."
              accent="AI orchestration second."
              description="Every card recommendation traces back to deterministic logic, not a language model improvising transfer ratios."
            />
            <div className="mt-16">
              <TrustPillars />
            </div>
          </Inner>
        </Bleed>

        {/* Example strategy output */}
        <Bleed banded className="py-32">
          <Inner>
            <SectionHeading
              eyebrow="What you actually get"
              title="A card strategy you can"
              accent="act on."
              description="Not a score or a vague tip. A concrete plan: which credit card for which spend, the transfer path, and a dated timeline."
            />
            <div className="mt-16">
              <StrategyOutput />
            </div>
          </Inner>
        </Bleed>

        {/* Supported cards */}
        <Bleed id="cards" className="py-32">
          <Inner>
            <SectionHeading
              eyebrow="Your existing wallet"
              title="The credit cards you already"
              accent="carry."
              description="OptiMiles maximizes the credit cards you already own before it ever recommends a new one."
            />
            <div className="mt-16">
              <SupportedCards />
            </div>
          </Inner>
        </Bleed>

        {/* Supported reward ecosystems */}
        <Bleed banded className="py-32">
          <Inner>
            <SectionHeading
              eyebrow="Supported ecosystems"
              title="Airlines, hotels,"
              accent="and your banks."
              description="Reward currencies and transfer partners across the programs that matter for Indian travel cards."
            />
            <div className="mt-16">
              <EcosystemMarquee />
            </div>
          </Inner>
        </Bleed>

        {/* Built for */}
        <Bleed className="py-32">
          <Inner>
            <SectionHeading
              eyebrow="Built for"
              title="However you think"
              accent="about rewards."
            />
            <div className="mt-16">
              <BuiltFor />
            </div>
          </Inner>
        </Bleed>

        {/* Capabilities (feature tabs) */}
        <Bleed id="features" banded className="py-32">
          <Inner>
            <SectionHeading
              eyebrow="Under the hood"
              title="One engine,"
              accent="four sharp tools."
              description="Outcomes come first, but if you want to look closer, here's what's doing the work."
            />
            <div className="mt-16">
              <FeatureTabs />
            </div>
          </Inner>
        </Bleed>

        {/* Why OptiMiles exists */}
        <Bleed className="py-36">
          <Inner className="flex justify-center">
            <FadeUp className="max-w-3xl text-center">
              <p className="text-xs uppercase tracking-[0.22em] text-gold">
                Why OptiMiles exists
              </p>
              <p className="mt-6 font-heading text-3xl leading-snug text-foreground sm:text-5xl">
                The seat you want already exists in the credit cards you already
                carry.
              </p>
              <p className="mx-auto mt-6 max-w-prose text-base leading-relaxed text-muted-foreground">
                Most people leave business class on the table, not because they
                have the wrong cards, but because no one ever told them which
                card to swipe for which purchase. OptiMiles closes that gap:
                every rupee mapped to a card, every transfer partner understood,
                every redemption a clear, provable path away.
              </p>
            </FadeUp>
          </Inner>
        </Bleed>

        <Separator className="bg-hairline" />

        {/* FAQ */}
        <Bleed id="faq" className="py-32">
          <Inner className="flex justify-center">
            <div className="w-full max-w-3xl">
              <SectionHeading
                eyebrow="FAQ"
                title="Questions,"
                accent="answered."
              />
              <div className="mt-12">
                <Faq />
              </div>
            </div>
          </Inner>
        </Bleed>

        {/* Final CTA */}
        <Bleed className="pb-32">
          <Inner>
            <FadeUp className="relative overflow-hidden rounded-[2.5rem] border border-white/10 bg-card/40 px-8 py-24 text-center shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] backdrop-blur-sm sm:px-16">
              <div className="pointer-events-none absolute inset-0 bg-aurora" />
              <div className="relative">
                <ShieldCheck className="mx-auto size-10 text-gold" />
                <h2 className="mx-auto mt-6 max-w-3xl font-heading text-3xl text-foreground sm:text-6xl">
                  Your next redemption is a card strategy away.
                </h2>
                <p className="mx-auto mt-5 max-w-xl text-muted-foreground">
                  Create a free account and let OptiMiles chart the most
                  efficient path from your credit card spending to your travel
                  goal.
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
            </FadeUp>
          </Inner>
        </Bleed>
      </main>

      <SiteFooter />
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
    <FadeUp className="mx-auto max-w-3xl text-center">
      <p className="text-xs uppercase tracking-[0.22em] text-gold">{eyebrow}</p>
      <h2 className="mt-4 font-heading text-4xl leading-[1.05] tracking-tight text-foreground sm:text-6xl">
        {title} {accent && <span className="italic text-gold">{accent}</span>}
      </h2>
      {description && (
        <p className="mx-auto mt-6 max-w-xl text-muted-foreground">
          {description}
        </p>
      )}
    </FadeUp>
  );
}
