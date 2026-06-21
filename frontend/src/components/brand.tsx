import Link from "next/link"

import { cn } from "@/lib/utils"

export function Brand({ className }: { className?: string }) {
  return (
    <Link
      href="/"
      className={cn("flex items-center gap-2", className)}
      aria-label="OptiMiles home"
    >
      <span className="grid size-7 place-items-center rounded-lg bg-gold/15 ring-1 ring-gold/30">
        <span className="size-1.5 rounded-full bg-gold" />
      </span>
      <span className="font-heading text-lg tracking-wide text-foreground">
        Opti<span className="text-gold">Miles</span>
      </span>
    </Link>
  )
}
