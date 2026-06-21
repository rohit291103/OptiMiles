"use client"

import * as React from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

type CarouselProps = {
  children: React.ReactNode
  className?: string
  /** Tailwind classes applied to every slide wrapper, e.g. basis/min-width control */
  itemClassName?: string
  /** Show prev/next arrow controls. Defaults to true. */
  controls?: boolean
  /** Accessible label for the carousel region. */
  label?: string
}

/**
 * Lightweight, dependency-free carousel built on CSS scroll-snap.
 * Pass slides as children; each child is wrapped in a snap item.
 */
export function Carousel({
  children,
  className,
  itemClassName,
  controls = true,
  label = "Carousel",
}: CarouselProps) {
  const scrollerRef = React.useRef<HTMLDivElement>(null)
  const [canPrev, setCanPrev] = React.useState(false)
  const [canNext, setCanNext] = React.useState(true)

  const updateButtons = React.useCallback(() => {
    const el = scrollerRef.current
    if (!el) return
    const { scrollLeft, scrollWidth, clientWidth } = el
    setCanPrev(scrollLeft > 4)
    setCanNext(scrollLeft + clientWidth < scrollWidth - 4)
  }, [])

  React.useEffect(() => {
    const el = scrollerRef.current
    if (!el) return
    updateButtons()
    el.addEventListener("scroll", updateButtons, { passive: true })
    window.addEventListener("resize", updateButtons)
    return () => {
      el.removeEventListener("scroll", updateButtons)
      window.removeEventListener("resize", updateButtons)
    }
  }, [updateButtons])

  function scrollByDir(dir: 1 | -1) {
    const el = scrollerRef.current
    if (!el) return
    el.scrollBy({ left: dir * el.clientWidth * 0.8, behavior: "smooth" })
  }

  const slides = React.Children.toArray(children)

  return (
    <div className={cn("relative", className)}>
      <div
        ref={scrollerRef}
        role="region"
        aria-label={label}
        className="-mx-1 flex snap-x snap-mandatory gap-4 overflow-x-auto scroll-smooth px-1 pb-4 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {slides.map((child, i) => (
          <div
            key={i}
            className={cn("shrink-0 snap-start", itemClassName)}
          >
            {child}
          </div>
        ))}
      </div>

      {controls && (
        <div className="mt-2 flex items-center justify-end gap-2">
          <Button
            type="button"
            size="icon"
            variant="outline"
            aria-label="Previous"
            disabled={!canPrev}
            onClick={() => scrollByDir(-1)}
            className="rounded-full border-hairline"
          >
            <ChevronLeft />
          </Button>
          <Button
            type="button"
            size="icon"
            variant="outline"
            aria-label="Next"
            disabled={!canNext}
            onClick={() => scrollByDir(1)}
            className="rounded-full border-hairline"
          >
            <ChevronRight />
          </Button>
        </div>
      )}
    </div>
  )
}
