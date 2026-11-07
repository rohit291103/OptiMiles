import Link from "next/link"
import { Globe, Mail } from "lucide-react"

import { Brand } from "@/components/brand"

const SOCIAL_LINKS = [
  { href: "mailto:hello@optimiles.app", label: "Email", icon: Mail },
  { href: "https://optimiles.app", label: "Website", icon: Globe },
]

const FOOTER_GROUPS = [
  {
    title: "Product",
    links: [
      { href: "/#how", label: "How it works" },
      { href: "/#features", label: "Features" },
      { href: "/#simulate", label: "Simulator" },
      { href: "/#cards", label: "Supported cards" },
    ],
  },
  {
    title: "Company",
    links: [
      { href: "/#faq", label: "FAQ" },
      { href: "/signup", label: "Get started" },
      { href: "/login", label: "Log in" },
    ],
  },
  {
    title: "Legal",
    links: [
      { href: "/privacy", label: "Privacy" },
      { href: "/terms", label: "Terms" },
      { href: "/terms#not-advice", label: "Disclosures" },
    ],
  },
]

export function SiteFooter() {
  return (
    <footer className="border-t border-hairline">
      <div className="w-full px-5 py-14 sm:px-8 lg:px-12 xl:px-16 2xl:px-24">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-[2fr_1fr_1fr_1fr]">
          <div className="max-w-sm">
            <Brand />
            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
              Credit card strategy for Indian travel rewards: which card to
              swipe, when to transfer, and what it gets you. No chatbot, no
              guesswork.
            </p>
            <div className="mt-6 flex items-center gap-2.5">
              {SOCIAL_LINKS.map((social) => (
                <Link
                  key={social.label}
                  href={social.href}
                  aria-label={social.label}
                  className="grid size-11 place-items-center rounded-lg bg-gold/10 sm:size-9 text-muted-foreground ring-1 ring-hairline transition-colors hover:bg-gold/15 hover:text-gold hover:ring-gold/30"
                >
                  <social.icon className="size-4" strokeWidth={1.75} />
                </Link>
              ))}
            </div>
          </div>

          {FOOTER_GROUPS.map((group) => (
            <div key={group.title}>
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground/70">
                {group.title}
              </p>
              {/* space-y collapses on mobile in favour of padded rows: an
                  18px-tall text link is effectively un-tappable with a thumb. */}
              <ul className="mt-4 space-y-1 text-sm sm:space-y-3">
                {group.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="-mx-2 inline-flex min-h-11 items-center px-2 text-muted-foreground transition-colors hover:text-foreground sm:mx-0 sm:min-h-0 sm:px-0"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col-reverse items-center justify-between gap-4 border-t border-hairline pt-6 sm:flex-row">
          <span className="text-sm text-muted-foreground/80">
            © {new Date().getFullYear()} OptiMiles. All rights reserved.
          </span>
          <span className="inline-flex items-center gap-2 text-xs text-muted-foreground/70">
            <span className="size-1.5 rounded-full bg-gold" />
            Credit card strategy for Indian travellers
          </span>
        </div>
      </div>
    </footer>
  )
}
