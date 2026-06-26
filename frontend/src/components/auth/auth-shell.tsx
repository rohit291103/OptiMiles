import Link from "next/link";
import { Check, Quote } from "lucide-react";

import { Brand } from "@/components/brand";

const HIGHLIGHTS = [
  "Cap- and milestone-aware spend routing",
  "Honest, redemption-grade point valuations",
  "Explainable strategy, every number sourced",
];

export function AuthShell({
  children,
  title,
  subtitle,
}: {
  children: React.ReactNode;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="bg-grain grid min-h-screen lg:grid-cols-2">
      {/* Form side */}
      <div className="flex flex-col px-6 py-8 sm:px-10">
        <Brand />
        <div className="flex flex-1 items-center justify-center py-10">
          <div className="w-full max-w-sm">
            <h1 className="font-heading text-3xl text-foreground">{title}</h1>
            <p className="mt-2 text-sm text-muted-foreground">{subtitle}</p>
            <div className="mt-8">{children}</div>
          </div>
        </div>
        <p className="text-center text-xs text-muted-foreground/70">
          <Link href="/" className="transition-colors hover:text-foreground">
            ← Back to home
          </Link>
        </p>
      </div>

      {/* Brand panel */}
      <div className="relative hidden overflow-hidden border-l border-hairline bg-card/30 lg:block">
        <div className="absolute inset-0 bg-aurora" />
        <div className="relative flex h-full flex-col justify-center px-14">
          <p className="text-xs uppercase tracking-[0.22em] text-gold">
            Reward intelligence
          </p>
          <h2 className="mt-4 max-w-md font-heading text-3xl leading-snug text-foreground">
            The most trustworthy AI reward strategist for{" "}
            <span className="italic text-gold">Indian travel rewards.</span>
          </h2>

          <ul className="mt-10 space-y-4">
            {HIGHLIGHTS.map((h) => (
              <li key={h} className="flex items-center gap-3 text-sm text-foreground/90">
                <span className="grid size-6 shrink-0 place-items-center rounded-full bg-gold/15 text-gold ring-1 ring-gold/25">
                  <Check className="size-3.5" />
                </span>
                {h}
              </li>
            ))}
          </ul>

          <figure className="mt-14 max-w-md rounded-2xl border border-hairline bg-card/60 p-6 backdrop-blur-sm">
            <Quote className="size-6 text-gold/60" />
            <blockquote className="mt-3 text-sm leading-relaxed text-foreground/90">
              “OptiMiles routed my spend and had me in business class in seven
              months, fully explained, every step.”
            </blockquote>
            <figcaption className="mt-3 text-xs text-muted-foreground">
              Aditya R. · Product Manager, Bengaluru
            </figcaption>
          </figure>
        </div>
      </div>
    </div>
  );
}
