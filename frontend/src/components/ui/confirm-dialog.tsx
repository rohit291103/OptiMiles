"use client";

import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * A centered, focus-trapped confirmation modal — the professional replacement
 * for cramped inline "click again to confirm" affordances. Rendered through a
 * portal so it escapes any overflow/stacking context of its trigger, dims the
 * page behind it, and returns focus to the trigger on close.
 *
 * Purely presentational: the caller owns open state and both actions. The
 * confirm button can show a busy label; while busy the dialog can't be
 * dismissed so a delete can't be double-fired or interrupted mid-flight.
 */
export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  busy = false,
  busyLabel,
  errorMessage,
  destructive = false,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  description: React.ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  busy?: boolean;
  busyLabel?: string;
  errorMessage?: string | null;
  destructive?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const reduced = useReducedMotion();
  const panelRef = useRef<HTMLDivElement>(null);
  const confirmRef = useRef<HTMLButtonElement>(null);

  // Read live values inside the key handler via refs so the listener effect
  // depends only on `open` — it won't tear down/re-bind (or flip body.overflow)
  // on every busy-state change. Synced in an effect (never written in render).
  const busyRef = useRef(busy);
  const cancelRef = useRef(onCancel);
  useEffect(() => {
    busyRef.current = busy;
    cancelRef.current = onCancel;
  });

  // While open: lock body scroll, handle Escape, and trap Tab focus inside the
  // dialog (only Cancel + Confirm are focusable, so cycle between them).
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busyRef.current) {
        cancelRef.current();
        return;
      }
      if (e.key === "Tab") {
        const focusable = panelRef.current?.querySelectorAll<HTMLElement>(
          "button:not([disabled])",
        );
        if (!focusable || focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        const active = document.activeElement;
        if (e.shiftKey && active === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && active === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKeyDown);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = prevOverflow;
    };
  }, [open]);

  // Move focus to the confirm action when the dialog opens.
  useEffect(() => {
    if (open) confirmRef.current?.focus();
  }, [open]);

  if (typeof document === "undefined") return null;

  return createPortal(
    <AnimatePresence>
      {open && (
        <div
          className="fixed inset-0 z-[100] grid place-items-center p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="confirm-dialog-title"
        >
          <motion.div
            className="absolute inset-0 bg-background/70 backdrop-blur-sm"
            initial={reduced ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={() => !busy && onCancel()}
          />
          <motion.div
            ref={panelRef}
            className="relative max-h-[85vh] w-full max-w-md overflow-y-auto rounded-2xl border border-hairline bg-card p-6 shadow-2xl shadow-black/50"
            initial={reduced ? false : { opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={reduced ? { opacity: 0 } : { opacity: 0, scale: 0.98, y: 8 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="flex gap-4">
              {destructive && (
                <span className="mt-0.5 grid size-10 shrink-0 place-items-center rounded-full border border-destructive/30 bg-destructive/10 text-destructive">
                  <AlertTriangle className="size-5" />
                </span>
              )}
              <div className="min-w-0">
                <h2
                  id="confirm-dialog-title"
                  className="font-heading text-lg text-foreground"
                >
                  {title}
                </h2>
                <div className="mt-1.5 text-sm text-muted-foreground">
                  {description}
                </div>
              </div>
            </div>

            {errorMessage && (
              <p
                className="mt-4 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
                role="alert"
              >
                {errorMessage}
              </p>
            )}

            <div className="mt-6 flex flex-col-reverse gap-2.5 sm:flex-row sm:justify-end">
              <Button
                variant="outline"
                onClick={onCancel}
                disabled={busy}
                className="border-hairline"
              >
                {cancelLabel}
              </Button>
              <Button
                ref={confirmRef}
                onClick={onConfirm}
                disabled={busy}
                className={cn(
                  destructive
                    ? "bg-destructive text-white hover:bg-destructive/90"
                    : "bg-gold text-gold-foreground hover:bg-gold/90",
                  "disabled:opacity-70",
                )}
              >
                {busy ? (busyLabel ?? "Working…") : confirmLabel}
              </Button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
