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
      { href: "#", label: "Privacy" },
      { href: "#", label: "Terms" },
      { href: "#", label: "Disclosures" },
    ],
  },
]

export function SiteFooter() {
  return (
    <footer className="border-t border-hairline">
      <div className="mx-auto max-w-6xl px-6 py-14">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-[1.4fr_1fr_1fr_1fr]">
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
                  className="grid size-9 place-items-center rounded-lg bg-gold/10 text-muted-foreground ring-1 ring-hairline transition-colors hover:bg-gold/15 hover:text-gold hover:ring-gold/30"
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
              <ul className="mt-4 space-y-3 text-sm">
                {group.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-muted-foreground transition-colors hover:text-foreground"
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
