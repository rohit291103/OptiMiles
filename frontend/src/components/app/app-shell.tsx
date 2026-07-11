"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  CreditCard,
  LayoutDashboard,
  LogOut,
  Menu,
  Plus,
  Sparkles,
  X,
} from "lucide-react";

import { Brand } from "@/components/brand";
import { Button } from "@/components/ui/button";
import { signOut, useAuth } from "@/lib/use-auth";
import { cn } from "@/lib/utils";

/**
 * The signed-in app frame: fixed left sidebar (nav + user), slim top bar
 * (page title + primary "New goal" action), content well. Same dark/gold
 * system as the marketing site but denser and quieter — no marketing chrome.
 *
 * Also the auth gate for everything under it: children render only once a
 * session exists; otherwise we bounce to /login. Pages inside the shell can
 * therefore assume a signed-in user.
 */

const NAV = [
  {
    href: "/goals",
    label: "Dashboard",
    icon: LayoutDashboard,
    // A goal detail page (/goals/<id>) is part of the Dashboard flow — keep
    // its nav item lit there; /goals/new belongs to the "New goal" item.
    isActive: (p: string) => p.startsWith("/goals") && p !== "/goals/new",
  },
  {
    href: "/goals/new",
    label: "New goal",
    icon: Sparkles,
    isActive: (p: string) => p === "/goals/new",
  },
  {
    href: "/cards",
    label: "Supported cards",
    icon: CreditCard,
    isActive: (p: string) => p.startsWith("/cards"),
  },
] as const;

/** Top-bar title per route; goal detail pages fall through to "Strategy". */
function pageTitle(pathname: string): string {
  if (pathname === "/goals") return "Dashboard";
  if (pathname === "/goals/new") return "New goal";
  if (pathname.startsWith("/cards")) return "Supported cards";
  if (pathname.startsWith("/goals/")) return "Strategy";
  return "Dashboard";
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, loading } = useAuth();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="grid min-h-dvh place-items-center bg-background">
        <p className="text-sm text-muted-foreground" role="status">
          Loading…
        </p>
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh bg-background">
      {/* ── Sidebar (desktop) ─────────────────────────────────────────── */}
      <aside className="sticky top-0 hidden h-dvh w-64 shrink-0 flex-col border-r border-hairline bg-card/30 lg:flex">
        <SidebarContent email={user.email ?? ""} pathname={pathname} />
      </aside>

      {/* ── Sidebar (mobile drawer) ───────────────────────────────────── */}
      {mobileNavOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            aria-label="Close menu"
            onClick={() => setMobileNavOpen(false)}
            className="absolute inset-0 bg-background/70 backdrop-blur-sm"
          />
          <aside className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col border-r border-hairline bg-card">
            <SidebarContent
              email={user.email ?? ""}
              pathname={pathname}
              onClose={() => setMobileNavOpen(false)}
              onNavigate={() => setMobileNavOpen(false)}
            />
          </aside>
        </div>
      )}

      {/* ── Main column ───────────────────────────────────────────────── */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-40 flex items-center justify-between gap-3 border-b border-hairline bg-background/85 px-4 py-3.5 backdrop-blur-md sm:px-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              aria-label="Open menu"
              onClick={() => setMobileNavOpen(true)}
              className="grid size-9 place-items-center rounded-lg border border-hairline text-foreground lg:hidden"
            >
              <Menu className="size-5" />
            </button>
            <h1 className="font-heading text-lg tracking-wide text-foreground sm:text-xl">
              {pageTitle(pathname)}
            </h1>
          </div>
          {pathname !== "/goals/new" && (
            <Button asChild className="bg-gold text-gold-foreground hover:bg-gold/90">
              <Link href="/goals/new">
                <Plus className="size-4" /> New goal
              </Link>
            </Button>
          )}
        </header>

        <main className="min-w-0 flex-1 px-4 py-8 sm:px-6 lg:px-10">
          <div className="mx-auto w-full max-w-5xl">{children}</div>
        </main>
      </div>
    </div>
  );
}

function SidebarContent({
  email,
  pathname,
  onClose,
  onNavigate,
}: {
  email: string;
  pathname: string;
  onClose?: () => void;
  onNavigate?: () => void;
}) {
  return (
    <>
      <div className="flex items-center justify-between px-5 py-5">
        <Brand />
        {onClose && (
          <button
            type="button"
            aria-label="Close menu"
            onClick={onClose}
            className="grid size-8 place-items-center rounded-lg border border-hairline text-foreground"
          >
            <X className="size-4" />
          </button>
        )}
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {NAV.map(({ href, label, icon: Icon, isActive }) => {
          const active = isActive(pathname);
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-3 text-[15px] transition-colors",
                active
                  ? "bg-gold/10 font-medium text-gold"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground",
              )}
            >
              <Icon className="size-[18px] shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-hairline px-5 py-4">
        <div className="flex items-center gap-3">
          <span className="grid size-8 shrink-0 place-items-center rounded-full bg-gold/15 text-xs font-semibold uppercase text-gold ring-1 ring-gold/30">
            {email.slice(0, 1) || "?"}
          </span>
          <span className="min-w-0 flex-1 truncate text-sm text-muted-foreground" title={email}>
            {email}
          </span>
          <button
            type="button"
            aria-label="Sign out"
            title="Sign out"
            onClick={() => signOut()}
            className="grid size-8 shrink-0 place-items-center rounded-lg text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
          >
            <LogOut className="size-4" />
          </button>
        </div>
      </div>
    </>
  );
}
