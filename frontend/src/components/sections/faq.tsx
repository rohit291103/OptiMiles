"use client";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

const FAQS = [
  {
    q: "Is OptiMiles a chatbot?",
    a: "No. OptiMiles is a deterministic reward optimization engine. Calculations come from a normalized reward schema and explicit logic — AI is only used to narrate and explain strategies, never to invent numbers or transfer ratios.",
  },
  {
    q: "Which credit cards are supported today?",
    a: "The MVP is live for HDFC Infinia, HDFC Diners Club Black, Axis Magnus, Axis Atlas, Amex Platinum Travel, and SBI Cashback. More cards are on the roadmap and rolling out incrementally.",
  },
  {
    q: "Do you track my spending automatically?",
    a: "No. OptiMiles does not parse SMS, scan statements, or auto-track transactions. You tell it your goal and spending profile, and it generates an explainable strategy. Your data stays yours.",
  },
  {
    q: "How accurate are the reward valuations?",
    a: "Points are valued by realistic redemption and transfer-partner value, not the bank's face value. Every valuation is versioned and auditable, so you can see exactly how a number was derived.",
  },
  {
    q: "Is it free to get started?",
    a: "You can create an account and run the simulator for free. Premium optimization features are part of the roadmap as the platform matures.",
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
