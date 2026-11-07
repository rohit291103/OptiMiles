import { Bleed, Inner } from "@/components/sections/section-shell";

export type LegalSection = { id?: string; title: string; body: React.ReactNode };

/** Plain-language legal page: title, last-updated date, numbered sections. */
export function LegalPage({
  eyebrow,
  title,
  updated,
  intro,
  sections,
}: {
  eyebrow: string;
  title: string;
  updated: string;
  intro: React.ReactNode;
  sections: LegalSection[];
}) {
  return (
    <Bleed className="border-b border-hairline py-12 sm:py-20">
      <Inner>
        <article className="max-w-2xl">
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-gold">{eyebrow}</p>
          <h1 className="mt-3 text-3xl font-semibold leading-tight sm:text-4xl">{title}</h1>
          <p className="mt-2 text-sm text-muted-foreground">Last updated {updated}</p>
          <div className="mt-6 space-y-4 text-base leading-relaxed text-muted-foreground">
            {intro}
          </div>
          <div className="mt-10 space-y-10">
            {sections.map((section, index) => (
              <section key={section.title} id={section.id} className="scroll-mt-24">
                <h2 className="text-lg font-semibold text-foreground">
                  {`${index + 1}. ${section.title}`}
                </h2>
                <div className="mt-3 space-y-3 text-[15px] leading-relaxed text-muted-foreground [&_a]:text-gold [&_a]:underline-offset-4 hover:[&_a]:underline [&_li]:ml-5 [&_li]:list-disc [&_strong]:text-foreground">
                  {section.body}
                </div>
              </section>
            ))}
          </div>
        </article>
      </Inner>
    </Bleed>
  );
}
