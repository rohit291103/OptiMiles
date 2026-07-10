"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Menu, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Brand } from "@/components/brand"
import { signOut, useAuth } from "@/lib/use-auth"

const LINKS = [
  { href: "/#simulate", label: "Simulator" },
  { href: "/#how", label: "How it works" },
  { href: "/#cards", label: "Supported cards" },
  { href: "/#features", label: "Features" },
  { href: "/#faq", label: "FAQ" },
]

export function SiteNav() {
  const [open, setOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const { user } = useAuth()

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24)
    onScroll()
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

  return (
    <header
      className={`sticky top-0 z-50 border-b backdrop-blur-md transition-colors duration-300 ${
        scrolled
          ? "border-hairline bg-background/85"
          : "border-transparent bg-background/0"
      }`}
    >
      <nav
        className={`flex w-full items-center justify-between px-5 transition-all duration-300 sm:px-8 lg:px-12 xl:px-16 2xl:px-24 ${
          scrolled ? "py-3" : "py-5"
        }`}
      >
        <Brand />

        <div className="hidden items-center gap-7 text-sm text-muted-foreground lg:flex">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="transition-colors hover:text-foreground"
            >
              {link.label}
            </Link>
          ))}
        </div>

        <div className="hidden items-center gap-3 sm:flex">
          {user ? (
            <>
              <Button asChild variant="ghost" size="lg" className="text-foreground hover:bg-secondary">
                <Link href="/goals">My goals</Link>
              </Button>
              <span className="max-w-56 truncate text-sm text-muted-foreground">
                {user.email}
              </span>
              <Button
                variant="ghost"
                size="lg"
                className="text-foreground hover:bg-secondary"
                onClick={() => signOut()}
              >
                Sign out
              </Button>
            </>
          ) : (
            <>
              <Button asChild variant="ghost" size="lg" className="text-foreground hover:bg-secondary">
                <Link href="/login">Log in</Link>
              </Button>
              <Button asChild size="lg" className="bg-gold text-gold-foreground hover:bg-gold/90">
                <Link href="/signup">Get started</Link>
              </Button>
            </>
          )}
        </div>

        <button
          type="button"
          aria-label="Toggle menu"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
          className="grid size-9 place-items-center rounded-lg border border-hairline text-foreground sm:hidden"
        >
          {open ? <Menu className="hidden" /> : null}
          {open ? <X className="size-5" /> : <Menu className="size-5" />}
        </button>
      </nav>

      {open && (
        <div className="border-t border-hairline bg-background/95 px-6 py-4 sm:hidden">
          <div className="flex flex-col gap-1">
            {LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className="rounded-lg px-2 py-2 text-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
              >
                {link.label}
              </Link>
            ))}
          </div>
          <div className="mt-4 flex flex-col gap-2">
            {user ? (
              <>
                <Button asChild variant="outline" className="border-hairline">
                  <Link href="/goals" onClick={() => setOpen(false)}>My goals</Link>
                </Button>
                <span className="px-2 text-sm text-muted-foreground">{user.email}</span>
                <Button
                  variant="outline"
                  className="border-hairline"
                  onClick={() => {
                    setOpen(false)
                    signOut()
                  }}
                >
                  Sign out
                </Button>
              </>
            ) : (
              <>
                <Button asChild variant="outline" className="border-hairline">
                  <Link href="/login" onClick={() => setOpen(false)}>Log in</Link>
                </Button>
                <Button asChild className="bg-gold text-gold-foreground hover:bg-gold/90">
                  <Link href="/signup" onClick={() => setOpen(false)}>Get started</Link>
                </Button>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  )
}
