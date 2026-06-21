"use client";

import { Quote, Star } from "lucide-react";

import { Carousel } from "@/components/ui/carousel";

const TESTIMONIALS = [
  {
    quote:
      "I'd been hoarding points across four cards with no plan. OptiMiles routed my spend and I had business-class to Singapore in seven months — fully explained, every step.",
    name: "Aditya R.",
    role: "Product Manager, Bengaluru",
  },
  {
    quote:
      "Finally a tool that tells me what a point is actually worth instead of the bank's marketing number. The valuation engine alone changed how I spend.",
    name: "Meera S.",
    role: "Consultant, Mumbai",
  },
  {
    quote:
      "It stopped me from wasting spend on a card after its cap was hit. The cap-aware routing is the feature I didn't know I needed.",
    name: "Karan V.",
    role: "Founder, Gurugram",
  },
  {
    quote:
      "No chatbot fluff. Every recommendation comes with the math behind it, so I actually trust it. That's rare in fintech.",
    name: "Priya N.",
    role: "Analyst, Hyderabad",
  },
];

export function Testimonials() {
  return (
    <Carousel label="Customer testimonials" itemClassName="w-[20rem] sm:w-[24rem]">
      {TESTIMONIALS.map((t) => (
        <figure
          key={t.name}
          className="flex h-full flex-col justify-between rounded-2xl border border-hairline bg-card/50 p-6 backdrop-blur-sm"
        >
          <div>
            <div className="flex items-center justify-between">
              <Quote className="size-7 text-gold/60" />
              <div className="flex gap-0.5">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Star key={i} className="size-3.5 fill-gold text-gold" />
                ))}
              </div>
            </div>
            <blockquote className="mt-4 text-sm leading-relaxed text-foreground/90">
              “{t.quote}”
            </blockquote>
          </div>
          <figcaption className="mt-6 border-t border-hairline pt-4">
            <p className="font-heading text-sm text-foreground">{t.name}</p>
            <p className="text-xs text-muted-foreground">{t.role}</p>
          </figcaption>
        </figure>
      ))}
    </Carousel>
  );
}
