# OptiMiles design system — how to build with it

OptiMiles is a **dark-only, gold-accented** product (Indian credit-card reward
optimization). Build every screen on the dark surface with gold reserved for the
single most important action or metric — never as a fill color for large areas.

## 1. Wrapping — required

Every screen must be wrapped in `DsThemeProvider` (exported from the bundle). It
applies the `.dark` class and the base `bg-background text-foreground` surface
that all the design tokens are defined under. **Without it, components render in
an unstyled light theme** (the gold/dark tokens only exist inside `.dark`).

```jsx
<DsThemeProvider>
  {/* your screen */}
</DsThemeProvider>
```

There is no light mode. Do not add a theme toggle.

## 2. Styling idiom — Tailwind utility classes against semantic tokens

This is a Tailwind v4 system. Style with these **semantic** utility classes (not
raw colors like `bg-zinc-900` — use the tokens so the brand stays consistent):

| Class | Use for |
|---|---|
| `bg-background` / `text-foreground` | base page surface + body text (provider sets these) |
| `bg-card` | raised panels, cards, sheets |
| `text-muted-foreground` | secondary / supporting text |
| `border-hairline` | thin dividers and card outlines (very low-contrast) |
| `bg-gold` / `text-gold-foreground` | the ONE primary action per view (a filled gold button) |
| `text-gold` | a single accented metric, label, or eyebrow — used sparingly |
| `ring-gold` / `ring-gold/25` | gold focus/emphasis rings on key elements |
| `font-heading` | headings — the Fraunces serif display face (h1–h3 get it automatically) |
| `bg-aurora` | soft gold radial glow behind a hero / CTA block |
| `bg-grain` | faint dotted page texture |

Tokens behind these (for `var(--*)` use): `--background`, `--foreground`,
`--card`, `--muted-foreground`, `--hairline`, `--gold`, `--gold-foreground`,
`--primary`. Gold is `--gold` (a warm oklch gold); pair it with
`--gold-foreground` (near-black) for text on gold.

## 3. The gold CTA is a className, NOT a Button variant

`Button` variants are `default | outline | secondary | ghost | destructive |
link` — **there is no `"gold"` variant.** The signature gold primary button is a
`default` button with a gold className override:

```jsx
<Button className="bg-gold text-gold-foreground hover:bg-gold/90">
  Build my card strategy
</Button>
```

Use exactly one gold CTA per view; everything else is `outline` / `ghost` /
`secondary`. Badges accent the same way: `<Badge className="bg-gold/15 text-gold
ring-1 ring-gold/25">High confidence</Badge>`.

## 4. Where the truth lives

Read these bound files before styling: the stylesheet closure starts at
`styles.css` (→ `_ds_bundle.css` for all token + utility definitions, → the
Fraunces `@font-face`). Per-component API + usage: each
`components/<group>/<Name>/<Name>.prompt.md` and `<Name>.d.ts`. The components
are `ui/` (Button, Badge, Card, Input) and `sections/` (HeroFlow, TrustPillars).
`Card` composes from `Card`, `CardHeader`, `CardTitle`, `CardDescription`,
`CardContent`, `CardFooter`, `CardAction`.

## 5. Idiomatic example

```jsx
<DsThemeProvider>
  <main className="bg-grain min-h-screen px-6 py-16">
    <p className="text-xs uppercase tracking-[0.2em] text-gold">Your goal</p>
    <h1 className="font-heading text-4xl text-foreground">
      Fly business class in 8 months.
    </h1>
    <Card className="mt-8 max-w-md">
      <CardHeader>
        <CardTitle>HDFC Infinia</CardTitle>
        <CardDescription>Best routed for travel and dining spend.</CardDescription>
        <CardAction>
          <Badge className="bg-gold/15 text-gold ring-1 ring-gold/25">Top pick</Badge>
        </CardAction>
      </CardHeader>
      <CardContent className="text-muted-foreground">
        Route grocery, travel, and online spend here to hit the milestone first.
      </CardContent>
      <CardFooter>
        <Button className="bg-gold text-gold-foreground hover:bg-gold/90">
          See strategy
        </Button>
      </CardFooter>
    </Card>
  </main>
</DsThemeProvider>
```
