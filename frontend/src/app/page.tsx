import Link from "next/link";
import { ArrowRight, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { FadeUp } from "@/components/ui/motion";
import { GoalSimulator } from "@/components/goal-simulator";
import { SiteNav } from "@/components/site-nav";
import { SiteFooter } from "@/components/site-footer";
import { PageFrame } from "@/components/page-frame";
import { Hero } from "@/components/sections/hero";
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

        {/* Dream outcomes */}
        <section className="mx-auto max-w-6xl px-6 pt-12 pb-28">
          <SectionHeading
            eyebrow="Where your card spend goes"
            title="Real trips,"
            accent="not just points."
            description="OptiMiles optimizes your credit card spend for goals achieved: the trip, the suite, the lounge, not points earned for their own sake."
          />
          <div className="mt-14">
            <DreamOutcomes />
          </div>
        </section>

        {/* How it works */}
        <section id="how" className="scroll-mt-24 border-y border-hairline bg-card/20">
          <HowItWorks />
        </section>

        {/* Why trust OptiMiles */}
        <section className="mx-auto max-w-6xl px-6 py-28">
          <SectionHeading
            eyebrow="Why trust OptiMiles"
            title="Structured card logic first."
            accent="AI orchestration second."
            description="Every card recommendation traces back to deterministic logic, not a language model improvising transfer ratios."
          />
          <div className="mt-14">
            <TrustPillars />
          </div>
        </section>

        {/* Goal simulator */}
        <section id="simulate" className="scroll-mt-24 border-y border-hairline bg-card/20 py-28">
          <div className="mx-auto max-w-6xl px-6">
            <SectionHeading
              eyebrow="Try it now"
              title="Pick your cards."
              accent="See the path."
              description="Pick a destination, a cabin, and the credit cards you carry, and watch your timeline resolve."
            />
            <div className="mt-14">
              <GoalSimulator />
            </div>
          </div>
        </section>

        {/* Example strategy output */}
        <section className="mx-auto max-w-6xl px-6 py-28">
          <SectionHeading
            eyebrow="What you actually get"
            title="A card strategy you can"
            accent="act on."
            description="Not a score or a vague tip. A concrete plan: which credit card for which spend, the transfer path, and a dated timeline."
          />
          <div className="mt-14">
            <StrategyOutput />
          </div>
        </section>

        {/* Supported cards */}
        <section id="cards" className="scroll-mt-24 border-y border-hairline bg-card/20 py-28">
          <div className="mx-auto max-w-6xl px-6">
            <SectionHeading
              eyebrow="Your existing wallet"
              title="The credit cards you already"
              accent="carry."
              description="OptiMiles maximizes the credit cards you already own before it ever recommends a new one."
            />
            <div className="mt-14">
              <SupportedCards />
            </div>
          </div>
        </section>

        {/* Supported reward ecosystems */}
        <section className="mx-auto max-w-6xl px-6 py-28">
          <SectionHeading
            eyebrow="Supported ecosystems"
            title="Airlines, hotels,"
            accent="and your banks."
            description="Reward currencies and transfer partners across the programs that matter for Indian travel cards."
          />
          <div className="mt-14">
            <EcosystemMarquee />
          </div>
        </section>

        {/* Built for */}
        <section className="mx-auto max-w-6xl px-6 py-28">
          <SectionHeading
            eyebrow="Built for"
            title="However you think"
            accent="about rewards."
          />
          <div className="mt-14">
            <BuiltFor />
          </div>
        </section>

        {/* Capabilities (feature tabs) */}
        <section id="features" className="scroll-mt-24 border-y border-hairline bg-card/20 py-28">
          <div className="mx-auto max-w-6xl px-6">
            <SectionHeading
              eyebrow="Under the hood"
              title="One engine,"
              accent="four sharp tools."
              description="Outcomes come first, but if you want to look closer, here's what's doing the work."
            />
            <div className="mt-14">
              <FeatureTabs />
            </div>
          </div>
        </section>

        {/* Why OptiMiles exists */}
        <section className="mx-auto max-w-3xl px-6 py-32 text-center">
          <FadeUp>
            <p className="text-xs uppercase tracking-[0.22em] text-gold">
              Why OptiMiles exists
            </p>
            <p className="mt-6 font-heading text-3xl leading-snug text-foreground sm:text-4xl">
              The seat you want already exists in the credit cards you already
              carry.
            </p>
            <p className="mt-6 text-base leading-relaxed text-muted-foreground">
              Most people leave business class on the table, not because they
              have the wrong cards, but because no one ever told them which card
              to swipe for which purchase. OptiMiles closes that gap: every
              rupee mapped to a card, every transfer partner understood, every
              redemption a clear, provable path away.
            </p>
          </FadeUp>
        </section>

        <Separator className="bg-hairline" />

        {/* FAQ */}
        <section id="faq" className="mx-auto max-w-3xl scroll-mt-24 px-6 py-28">
          <SectionHeading eyebrow="FAQ" title="Questions," accent="answered." />
          <div className="mt-12">
            <Faq />
          </div>
        </section>

        {/* Final CTA */}
        <section className="mx-auto max-w-6xl px-6 pb-28">
          <FadeUp className="relative overflow-hidden rounded-[2rem] border border-white/10 bg-card/40 px-8 py-20 text-center shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] backdrop-blur-sm sm:px-16">
            <div className="pointer-events-none absolute inset-0 bg-aurora" />
            <div className="relative">
              <ShieldCheck className="mx-auto size-10 text-gold" />
              <h2 className="mx-auto mt-6 max-w-2xl font-heading text-3xl text-foreground sm:text-5xl">
                Your next redemption is a card strategy away.
              </h2>
              <p className="mx-auto mt-5 max-w-xl text-muted-foreground">
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
          </FadeUp>
        </section>
      </main>

      <SiteFooter />

      <PageFrame />
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
    <FadeUp className="mx-auto max-w-2xl text-center">
      <p className="text-xs uppercase tracking-[0.22em] text-gold">{eyebrow}</p>
      <h2 className="mt-4 font-heading text-3xl tracking-tight text-foreground sm:text-5xl">
        {title} {accent && <span className="italic text-gold">{accent}</span>}
      </h2>
      {description && (
        <p className="mx-auto mt-5 max-w-xl text-muted-foreground">
          {description}
        </p>
      )}
    </FadeUp>
  );
}
