"use client";

import { useState } from "react";
import { ArrowRight, Plane, Sparkles, TrendingUp } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { CountUp } from "@/components/ui/count-up";

const DESTINATIONS = [
  { label: "Singapore", months: 7, businessMiles: 35000 },
  { label: "Dubai", months: 6, businessMiles: 30000 },
  { label: "London", months: 11, businessMiles: 67500 },
  { label: "New York", months: 14, businessMiles: 84500 },
];

const CABINS = [
  { label: "Economy", factor: 0.45 },
  { label: "Business", factor: 1 },
  { label: "First", factor: 1.6 },
];

const CARD_OPTIONS = [
  "HDFC Infinia",
  "HDFC Diners Club Black",
  "Axis Atlas",
  "Axis Magnus",
  "Amex Platinum Travel",
];

const AIRLINE_PREFS = ["No preference", "Star Alliance", "Oneworld", "SkyTeam"];

type Result = {
  destination: string;
  cabin: string;
  months: number;
  milesNeeded: number;
  monthlyMiles: number;
  progress: number;
  strategy: string;
  achievable: boolean;
};

export function GoalSimulator() {
  const [destination, setDestination] = useState(DESTINATIONS[0].label);
  const [cabin, setCabin] = useState("Business");
  const [monthlySpend, setMonthlySpend] = useState("100000");
  const [cards, setCards] = useState<string[]>(["HDFC Infinia", "Axis Atlas"]);
  const [timeline, setTimeline] = useState("12");
  const [airline, setAirline] = useState(AIRLINE_PREFS[0]);
  const [result, setResult] = useState<Result | null>(null);

  function toggleCard(name: string) {
    setCards((prev) =>
      prev.includes(name)
        ? prev.filter((c) => c !== name)
        : [...prev, name]
    );
  }

  function handleCalculate() {
    const target =
      DESTINATIONS.find((d) => d.label === destination) ?? DESTINATIONS[0];
    const cabinDef = CABINS.find((c) => c.label === cabin) ?? CABINS[1];
    const milesNeeded = Math.round(target.businessMiles * cabinDef.factor);
    // Illustrative earn rate: ~1.25 reward points per ₹ on the best route.
    const monthlyMiles = Math.round((Number(monthlySpend) || 0) * 1.25);
    const horizon = Math.max(Number(timeline) || target.months, 1);
    const accrued = monthlyMiles * horizon;
    const progress = Math.min(
      100,
      Math.round((accrued / Math.max(milesNeeded, 1)) * 100)
    );
    const strategy =
      cards.length >= 2
        ? `${cards[0]} + ${cards[1]} → frequent-flyer transfer (1:1)`
        : cards.length === 1
          ? `${cards[0]} → frequent-flyer transfer (1:1)`
          : "Add a card to see a routing strategy";

    setResult({
      destination: target.label,
      cabin,
      months: horizon,
      milesNeeded,
      monthlyMiles,
      progress,
      strategy,
      achievable: progress >= 100,
    });
  }

  return (
    <div className="overflow-hidden rounded-3xl border border-hairline bg-card/60 backdrop-blur-sm">
      <div className="border-b border-hairline px-6 py-5 sm:px-8">
        <p className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-gold">
          <Sparkles className="size-3.5" /> Goal simulator
        </p>
        <h3 className="mt-2 font-heading text-xl text-foreground sm:text-2xl">
          I want to fly{" "}
          <span className="italic text-gold">{cabin.toLowerCase()} class</span>{" "}
          to <span className="italic text-gold">{destination}</span>
        </h3>
      </div>

      <div className="p-6 sm:p-8">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="destination" className="text-muted-foreground">
              Destination
            </Label>
            <select
              id="destination"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              className="flex h-10 w-full rounded-lg border border-input bg-input/30 px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            >
              {DESTINATIONS.map((d) => (
                <option key={d.label} value={d.label} className="bg-card">
                  {d.label}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="spend" className="text-muted-foreground">
              Monthly spend (₹)
            </Label>
            <Input
              id="spend"
              type="number"
              value={monthlySpend}
              onChange={(e) => setMonthlySpend(e.target.value)}
              className="h-10 bg-input/30"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="timeline" className="text-muted-foreground">
              Timeline (months)
            </Label>
            <Input
              id="timeline"
              type="number"
              min={1}
              value={timeline}
              onChange={(e) => setTimeline(e.target.value)}
              className="h-10 bg-input/30"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="airline" className="text-muted-foreground">
              Preferred airline
            </Label>
            <select
              id="airline"
              value={airline}
              onChange={(e) => setAirline(e.target.value)}
              className="flex h-10 w-full rounded-lg border border-input bg-input/30 px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            >
              {AIRLINE_PREFS.map((a) => (
                <option key={a} value={a} className="bg-card">
                  {a}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-4 space-y-2">
          <Label className="text-muted-foreground">Cabin class</Label>
          <div className="inline-flex w-full rounded-lg border border-hairline bg-input/20 p-1 sm:w-auto">
            {CABINS.map((c) => (
              <button
                key={c.label}
                type="button"
                onClick={() => setCabin(c.label)}
                className={`flex-1 rounded-md px-4 py-1.5 text-sm font-medium transition-colors sm:flex-none ${
                  cabin === c.label
                    ? "bg-gold text-gold-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {c.label}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-4 space-y-2">
          <Label className="text-muted-foreground">Current cards</Label>
          <div className="flex flex-wrap gap-2">
            {CARD_OPTIONS.map((name) => {
              const selected = cards.includes(name);
              return (
                <button
                  key={name}
                  type="button"
                  onClick={() => toggleCard(name)}
                  aria-pressed={selected}
                  className={`rounded-full border px-3.5 py-1.5 text-xs font-medium transition-colors ${
                    selected
                      ? "border-gold/40 bg-gold/15 text-gold"
                      : "border-hairline text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {name}
                </button>
              );
            })}
          </div>
        </div>

        <Button
          onClick={handleCalculate}
          size="lg"
          className="mt-6 w-full bg-gold text-gold-foreground hover:bg-gold/90 sm:w-auto"
        >
          Build my reward strategy <ArrowRight />
        </Button>

        {result && (
          <div className="mt-8 space-y-6 border-t border-hairline pt-6">
            <div className="grid gap-4 sm:grid-cols-3">
              <Stat
                icon={<Plane className="size-4" />}
                label="Miles required"
                value={<CountUp value={result.milesNeeded} />}
              />
              <Stat
                icon={<TrendingUp className="size-4" />}
                label="Earned / month"
                value={<CountUp value={result.monthlyMiles} prefix="~" />}
              />
              <Stat
                label="Time to goal"
                value={`${result.months} months`}
              />
            </div>

            <div>
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Projected progress in {result.months} months</span>
                <span className="font-medium text-foreground">
                  {result.progress}%
                </span>
              </div>
              <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-input/40">
                <div
                  className="h-full rounded-full bg-gold transition-all duration-700"
                  style={{ width: `${result.progress}%` }}
                />
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 rounded-xl border border-hairline bg-background/40 p-4">
              <Badge className="bg-gold text-gold-foreground hover:bg-gold/90">
                {result.achievable ? "Achievable" : "Recommended route"}
              </Badge>
              <span className="text-sm text-foreground">{result.strategy}</span>
            </div>

            <p className="text-xs text-muted-foreground/70">
              Illustrative estimate. Real strategies account for caps,
              exclusions, milestones, and live transfer ratios.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  icon,
}: {
  label: string;
  value: React.ReactNode;
  icon?: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-hairline bg-background/40 p-4">
      <p className="flex items-center gap-1.5 text-xs uppercase tracking-[0.12em] text-muted-foreground">
        {icon}
        {label}
      </p>
      <p className="mt-1.5 font-heading text-xl text-foreground">{value}</p>
    </div>
  );
}
