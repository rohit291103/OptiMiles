import Link from "next/link";
import {
  ArrowRight,
  Sparkles,
  ShieldCheck,
  Route,
  LineChart,
  TrendingUp,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { GoalSimulator } from "@/components/goal-simulator";
import { SiteNav } from "@/components/site-nav";
import { SiteFooter } from "@/components/site-footer";
import { FeatureTabs } from "@/components/sections/feature-tabs";
import { SupportedCards } from "@/components/sections/supported-cards";
import { Testimonials } from "@/components/sections/testimonials";
import { Faq } from "@/components/sections/faq";

const STATS = [
  { value: "6", label: "Cards live in MVP" },
  { value: "1:1", label: "Best transfer ratios" },
  { value: "100%", label: "Explainable outputs" },
  { value: "0", label: "Guessed numbers" },
];

const STEPS = [
  {
    index: "01",
    icon: Route,
    title: "Reward Knowledge Engine",
    description:
      "Every card, transfer ratio, milestone, and cap normalized and versioned. Nothing is guessed; nothing is hallucinated.",
  },
  {
    index: "02",
    icon: TrendingUp,
    title: "Optimization Engine",
    description:
      "Your spend is routed across cards to maximize miles earned per rupee, against real-world caps and exclusions.",
  },
  {
    index: "03",
    icon: LineChart,
    title: "Simulation Engine",
    description:
      "Project your accumulation timeline against a single goal a route, a cabin, a date and watch the path resolve.",
  },
];

export default function Home() {
  return (
    <div className="bg-grain min-h-screen">
      <SiteNav />

      <main>
        {/* Hero */}
        <section className="relative overflow-hidden">
          <div className="pointer-events-none absolute inset-0 bg-aurora" />
          <div className="relative mx-auto max-w-6xl px-6 pt-20 pb-20 sm:pt-28">
            <div className="inline-flex items-center gap-2 rounded-full border border-hairline bg-card/50 px-4 py-1.5 text-xs text-muted-foreground backdrop-blur-sm">
              <Sparkles className="size-3.5 text-gold" />
              Reward intelligence for Indian travel cards
            </div>
            <h1 className="text-balance mt-6 max-w-3xl font-heading text-4xl leading-[1.1] text-foreground sm:text-6xl">
              Turn everyday spend into{" "}
              <span className="italic text-gold">business class</span>,
              deliberately.
            </h1>
            <p className="mt-6 max-w-xl text-base leading-relaxed text-muted-foreground sm:text-lg">
              OptiMiles is a reward optimization engine for Indian travel credit
              cards built to route your spend, value your points, and chart an
              explainable path to your next redemption. No chatbot. No guesswork.
            </p>
            <div className="mt-10 flex flex-wrap items-center gap-3">
              <Button
                asChild
                size="lg"
                className="bg-gold text-gold-foreground hover:bg-gold/90"
              >
                <Link href="/signup">
                  Plan my redemption <ArrowRight />
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
            </div>

            {/* Stats */}
            <dl className="mt-16 grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-hairline bg-hairline sm:grid-cols-4">
              {STATS.map((stat) => (
                <div key={stat.label} className="bg-background/60 px-5 py-6 backdrop-blur-sm">
                  <dt className="font-heading text-3xl text-gold">{stat.value}</dt>
                  <dd className="mt-1 text-xs uppercase tracking-[0.12em] text-muted-foreground">
                    {stat.label}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        </section>

        {/* How it works */}
        <section id="how" className="mx-auto max-w-6xl scroll-mt-24 px-6 py-20">
          <SectionHeading
            eyebrow="How it works"
            title="Structured systems first."
            accent="AI orchestration second."
            description="Every recommendation traces back to deterministic logic — not a language model improvising transfer ratios."
          />
          <div className="mt-14 grid gap-6 md:grid-cols-3">
            {STEPS.map((step) => (
              <div
                key={step.index}
                className="group relative rounded-2xl border border-hairline bg-card/40 p-7 backdrop-blur-sm transition-colors hover:border-gold/40"
              >
                <div className="flex items-center justify-between">
                  <span className="inline-flex size-11 items-center justify-center rounded-xl bg-gold/15 text-gold ring-1 ring-gold/25">
                    <step.icon className="size-5" />
                  </span>
                  <span className="font-heading text-sm text-muted-foreground/60">
                    {step.index}
                  </span>
                </div>
                <h3 className="mt-5 font-heading text-xl text-foreground">
                  {step.title}
                </h3>
                <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                  {step.description}
                </p>
              </div>
            ))}
          </div>
        </section>

        <Separator className="bg-hairline" />

        {/* Features (tabs) */}
        <section id="features" className="mx-auto max-w-6xl scroll-mt-24 px-6 py-20">
          <SectionHeading
            eyebrow="Capabilities"
            title="One engine,"
            accent="four sharp tools."
            description="From spend routing to redemption-readiness — explore what OptiMiles does under the hood."
          />
          <div className="mt-12">
            <FeatureTabs />
          </div>
        </section>

        {/* Supported cards (carousel) */}
        <section id="cards" className="scroll-mt-24 border-y border-hairline bg-card/20 py-20">
          <div className="mx-auto max-w-6xl px-6">
            <SectionHeading
              eyebrow="Built for"
              title="The cards you already"
              accent="carry."
              description="Active cards are live in the optimizer today. Others are on the MVP roadmap."
            />
            <div className="mt-12">
              <SupportedCards />
            </div>
          </div>
        </section>

        {/* Simulator */}
        <section id="simulate" className="mx-auto max-w-6xl scroll-mt-24 px-6 py-20">
          <SectionHeading
            eyebrow="Live demo"
            title="Set a goal."
            accent="See the path."
            description="A taste of the simulation engine — pick a destination and cabin, and watch your timeline resolve."
          />
          <div className="mt-12">
            <GoalSimulator />
          </div>
        </section>

        <Separator className="bg-hairline" />

        {/* Testimonials */}
        <section className="mx-auto max-w-6xl px-6 py-20">
          <SectionHeading
            eyebrow="Loved by deliberate travellers"
            title="Strategy you can"
            accent="actually trust."
          />
          <div className="mt-12">
            <Testimonials />
          </div>
        </section>

        {/* FAQ */}
        <section id="faq" className="mx-auto max-w-3xl scroll-mt-24 px-6 py-20">
          <SectionHeading
            eyebrow="FAQ"
            title="Questions,"
            accent="answered."
          />
          <div className="mt-10">
            <Faq />
          </div>
        </section>

        {/* CTA */}
        <section className="mx-auto max-w-6xl px-6 pb-24">
          <div className="relative overflow-hidden rounded-3xl border border-hairline bg-card/40 px-8 py-16 text-center backdrop-blur-sm sm:px-16">
            <div className="pointer-events-none absolute inset-0 bg-aurora" />
            <div className="relative">
              <ShieldCheck className="mx-auto size-10 text-gold" />
              <h2 className="mx-auto mt-6 max-w-2xl font-heading text-3xl text-foreground sm:text-4xl">
                Your next redemption is a strategy away.
              </h2>
              <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
                Create a free account and let OptiMiles chart the most efficient
                path from your spend to the cabin you want.
              </p>
              <div className="mt-8 flex flex-wrap justify-center gap-3">
                <Button
                  asChild
                  size="lg"
                  className="bg-gold text-gold-foreground hover:bg-gold/90"
                >
                  <Link href="/signup">
                    Get started free <ArrowRight />
                  </Link>
                </Button>
                <Button
                  asChild
                  size="lg"
                  variant="outline"
                  className="border-hairline"
                >
                  <Link href="/login">Log in</Link>
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
    <div className="max-w-2xl">
      <p className="text-xs uppercase tracking-[0.22em] text-gold">{eyebrow}</p>
      <h2 className="mt-4 font-heading text-3xl text-foreground sm:text-4xl">
        {title}{" "}
        {accent && <span className="italic text-gold">{accent}</span>}
      </h2>
      {description && (
        <p className="mt-4 text-muted-foreground">{description}</p>
      )}
    </div>
  );
}
