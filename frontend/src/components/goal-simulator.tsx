"use client";

import { useState } from "react";
import { ArrowRight, Plane, Sparkles, TrendingUp } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

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

type Result = {
  destination: string;
  cabin: string;
  months: number;
  milesNeeded: number;
  bestCard: string;
  monthlyMiles: number;
  progress: number;
};

export function GoalSimulator() {
  const [destination, setDestination] = useState(DESTINATIONS[0].label);
  const [cabin, setCabin] = useState("Business");
  const [monthlySpend, setMonthlySpend] = useState("180000");
  const [result, setResult] = useState<Result | null>(null);

  function handleCalculate() {
    const target =
      DESTINATIONS.find((d) => d.label === destination) ?? DESTINATIONS[0];
    const cabinDef = CABINS.find((c) => c.label === cabin) ?? CABINS[1];
    const milesNeeded = Math.round(target.businessMiles * cabinDef.factor);
    // Illustrative earn rate: ~1.25 reward points per ₹ on the best route.
    const monthlyMiles = Math.round((Number(monthlySpend) || 0) * 1.25);
    const accrued = monthlyMiles * target.months;
    const progress = Math.min(
      100,
      Math.round((accrued / Math.max(milesNeeded, 1)) * 100)
    );
    setResult({
      destination: target.label,
      cabin,
      months: target.months,
      milesNeeded,
      bestCard: "HDFC Infinia → frequent-flyer transfer (1:1)",
      monthlyMiles,
      progress,
    });
  }

  return (
    <div className="overflow-hidden rounded-3xl border border-hairline bg-card/60 backdrop-blur-sm">
      <div className="border-b border-hairline px-6 py-5 sm:px-8">
        <p className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-gold">
          <Sparkles className="size-3.5" /> Try the engine
        </p>
        <h3 className="mt-2 font-heading text-xl text-foreground sm:text-2xl">
          I want to fly{" "}
          <span className="italic text-gold">{cabin.toLowerCase()} class</span> to{" "}
          <span className="italic text-gold">{destination}</span>
        </h3>
      </div>

      <div className="p-6 sm:p-8">
        <div className="grid gap-4 sm:grid-cols-2 sm:items-end">
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

        <Button
          onClick={handleCalculate}
          size="lg"
          className="mt-6 w-full bg-gold text-gold-foreground hover:bg-gold/90 sm:w-auto"
        >
          Calculate my strategy <ArrowRight />
        </Button>

        {result && (
          <div className="mt-8 space-y-6 border-t border-hairline pt-6">
            <div className="grid gap-4 sm:grid-cols-3">
              <Stat
                icon={<Plane className="size-4" />}
                label="Miles required"
                value={result.milesNeeded.toLocaleString("en-IN")}
              />
              <Stat
                icon={<TrendingUp className="size-4" />}
                label="Earned / month"
                value={`~${result.monthlyMiles.toLocaleString("en-IN")}`}
              />
              <Stat label="Time to goal" value={`${result.months} months`} />
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
                Recommended route
              </Badge>
              <span className="text-sm text-foreground">{result.bestCard}</span>
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
  value: string;
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
