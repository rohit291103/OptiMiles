import type { Metadata } from "next";

import { LegalPage } from "@/components/legal-page";
import { SiteFooter } from "@/components/site-footer";
import { SiteNav } from "@/components/site-nav";

export const metadata: Metadata = {
  title: "Privacy policy — OptiMiles",
  description: "What OptiMiles collects, why, who processes it, and how to delete it.",
};

const CONTACT = "rohitg291103@gmail.com";

/**
 * Written from what the code actually does (2026-11-07 audit): Supabase Auth
 * (email/password or Google), saved goals and activity in Supabase Postgres,
 * the card picker in localStorage, plan summaries — no identity — sent to an
 * LLM via OpenRouter for narration, and no analytics or ad trackers.
 * Update this page whenever any of that changes.
 */
export default function PrivacyPage() {
  return (
    <main className="min-h-screen">
      <SiteNav />
      <LegalPage
        eyebrow="Legal"
        title="Privacy policy"
        updated="7 November 2026"
        intro={
          <p>
            OptiMiles helps you work out which credit card to use and how to reach a
            travel goal with reward points. This page explains, in plain words, what
            we collect to do that, who helps us run the service, and how to have your
            data deleted.
          </p>
        }
        sections={[
          {
            title: "What we collect",
            body: (
              <>
                <p>
                  <strong>Your account.</strong>{" "}If you sign up, we store your email
                  address. If you sign in with Google, Google shares your name, email
                  address and profile picture with us — nothing else. If you use a
                  password, it is stored only as a secure hash by our authentication
                  provider; we never see it.
                </p>
                <p>
                  <strong>What you choose to save.</strong>{" "}Travel goals and the plans
                  we calculate for them, the cards you hold, and any spends, lounge
                  visits and card renewal months you log.
                </p>
                <p>
                  <strong>What you type into a calculation.</strong>{" "}Amounts, spend
                  categories, destinations and card choices are sent to our server to
                  work out an answer. They are not stored unless you save them to your
                  account.
                </p>
                <p>
                  <strong>On your own device.</strong>{" "}The cards you pick on the Best
                  Card and goal pages are remembered in your browser&apos;s local
                  storage, so you don&apos;t have to pick them again. You can clear it
                  at any time from your browser settings.
                </p>
              </>
            ),
          },
          {
            title: "What we don't collect",
            body: (
              <ul>
                <li>Card numbers, bank account details, statements or SMS messages.</li>
                <li>Access to your bank or card accounts — we never connect to them.</li>
                <li>Advertising or analytics trackers. We don&apos;t sell or rent your data.</li>
              </ul>
            ),
          },
          {
            title: "How we use it",
            body: (
              <ul>
                <li>To calculate card recommendations and goal plans for you.</li>
                <li>To keep your saved goals and logged activity in your account.</li>
                <li>To sign you in and keep your account secure.</li>
              </ul>
            ),
          },
          {
            title: "AI-written explanations",
            body: (
              <p>
                To explain a plan in plain English, we send a summary of the calculated
                plan — figures, card names and the destination — to an AI model through
                OpenRouter. Your name, email address and account ID are not included.
                Every number is calculated by our own code; the AI only writes the
                wording, and if it is unavailable we use a fixed template instead.
              </p>
            ),
          },
          {
            title: "Who processes your data",
            body: (
              <>
                <p>We use these providers to run OptiMiles:</p>
                <ul>
                  <li><strong>Supabase</strong>{" "}— sign-in and the database that holds your account and saved data.</li>
                  <li><strong>Render</strong>{" "}— the server that runs our calculations.</li>
                  <li><strong>Vercel</strong>{" "}— hosting for this website.</li>
                  <li><strong>OpenRouter</strong>{" "}— routing to the AI model that writes explanations (see above).</li>
                  <li><strong>Google</strong>{" "}— only if you choose to sign in with Google.</li>
                </ul>
                <p>
                  These providers may process data outside India. They act on our
                  behalf and under their own security and privacy commitments.
                </p>
              </>
            ),
          },
          {
            title: "How long we keep it, and deleting it",
            body: (
              <>
                <p>
                  We keep your account data for as long as your account exists. You can
                  delete saved goals yourself in the app at any time.
                </p>
                <p>
                  To delete your account and everything linked to it, email{" "}
                  <a href={`mailto:${CONTACT}`}>{CONTACT}</a> from the address you
                  signed up with. We&apos;ll delete it within 30 days and confirm when
                  it&apos;s done.
                </p>
              </>
            ),
          },
          {
            title: "Security",
            body: (
              <p>
                All traffic is encrypted in transit, and access to the database is
                restricted. No online service is perfectly secure, so please use a
                strong password if you sign up with one.
              </p>
            ),
          },
          {
            title: "Children",
            body: <p>OptiMiles is meant for adults who hold credit cards, and is not intended for anyone under 18.</p>,
          },
          {
            title: "Changes and contact",
            body: (
              <p>
                If this policy changes, we&apos;ll update the date at the top. Questions
                or requests: <a href={`mailto:${CONTACT}`}>{CONTACT}</a>.
              </p>
            ),
          },
        ]}
      />
      <SiteFooter />
    </main>
  );
}
