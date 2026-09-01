import Link from "next/link"

import { cn } from "@/lib/utils"

export function Brand({ className }: { className?: string }) {
  return (
    <Link
      href="/"
      // min-h-11 on phones: the wordmark is a link home, and 28px of height
      // is not a thumb target.
      className={cn("flex min-h-11 items-center gap-2 sm:min-h-0", className)}
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
