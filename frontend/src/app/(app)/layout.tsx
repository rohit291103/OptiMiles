import { AppShell } from "@/components/app/app-shell";

/**
 * Route group for the signed-in product surface (/goals, /goals/new,
 * /goals/[id], /cards): one shared shell — sidebar, top bar, auth gate —
 * kept out of the marketing site's routes.
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
