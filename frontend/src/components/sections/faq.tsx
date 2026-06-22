"use client";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

const FAQS = [
  {
    q: "What cards are supported?",
    a: "OptiMiles is live for HDFC Infinia, HDFC Diners Club Black, HDFC Regalia Gold, and HSBC TravelOne today. More cards are on the roadmap and rolling out incrementally.",
  },
  {
    q: "Can I use the cards I already have?",
    a: "Yes that's the whole point. OptiMiles maximizes the cards already in your wallet before it ever suggests applying for a new one.",
  },
  {
    q: "Do I need to apply for new cards?",
    a: "No. OptiMiles first finds the best strategy with your existing cards. A new card is only ever suggested when it meaningfully shortens your path to a goal, with the reasoning shown.",
  },
  {
    q: "Do you connect to my bank accounts?",
    a: "No. OptiMiles does not parse SMS, scan statements, or auto-track transactions. You tell it your goal and spending profile, and it generates an explainable strategy. Your data stays yours.",
  },
  {
    q: "Is this a chatbot?",
    a: "No. OptiMiles is a deterministic reward optimization engine. Calculations come from a normalized reward schema and explicit logic — AI is only used to narrate and explain strategies, never to invent numbers or transfer ratios.",
  },
  {
    q: "How do reward projections work?",
    a: "We model your spending against each card's earn rates, caps, exclusions, and milestones, then project your accumulation month by month toward a single goal. Every projection traces back to versioned, auditable rules.",
  },
  {
    q: "How accurate are the calculations?",
    a: "Points are valued by realistic redemption and transfer-partner value, not the bank's face value and every value is versioned and auditable, so you can see exactly how a number was derived.",
  },
];

export function Faq() {
  return (
    <Accordion type="single" collapsible className="w-full">
      {FAQS.map((item) => (
        <AccordionItem key={item.q} value={item.q}>
          <AccordionTrigger>{item.q}</AccordionTrigger>
          <AccordionContent>{item.a}</AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  );
}
