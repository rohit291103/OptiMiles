import type { Metadata } from "next";

import { LegalPage } from "@/components/legal-page";
import { SiteFooter } from "@/components/site-footer";
import { SiteNav } from "@/components/site-nav";

export const metadata: Metadata = {
  title: "Terms of service — OptiMiles",
  description: "The terms for using OptiMiles, including what our figures are and aren't.",
};

const CONTACT = "rohitg291103@gmail.com";

export default function TermsPage() {
  return (
    <main className="min-h-screen">
      <SiteNav />
      <LegalPage
        eyebrow="Legal"
        title="Terms of service"
        updated="7 November 2026"
        intro={
          <p>
            By using OptiMiles you agree to these terms. They are short and written to
            be read — please do.
          </p>
        }
        sections={[
          {
            title: "What OptiMiles is",
            body: (
              <p>
                OptiMiles is an information tool. It estimates the rewards your credit
                cards earn and how to reach a travel goal with them. It is not a bank,
                a card issuer or a financial adviser, and it is not affiliated with any
                bank, card network, airline or hotel programme.
              </p>
            ),
          },
          {
            id: "not-advice",
            title: "Our figures are estimates, not advice",
            body: (
              <>
                <p>
                  Earn rates, caps, transfer ratios and award prices come from
                  published sources, and issuers change them — sometimes without
                  notice. Figures we haven&apos;t yet checked line by line are marked
                  with an asterisk (*). Monthly caps are assumed unused unless you log
                  your spending.
                </p>
                <p>
                  <strong>Always confirm with your card issuer or the programme before
                  you spend, apply for a card or transfer points.</strong>{" "}You are
                  responsible for your financial decisions; nothing on OptiMiles is
                  financial, tax or legal advice.
                </p>
              </>
            ),
          },
          {
            title: "Your account",
            body: (
              <ul>
                <li>Keep your sign-in details safe; you&apos;re responsible for activity on your account.</li>
                <li>One account per person, with accurate information.</li>
                <li>You can stop using OptiMiles and ask us to delete your account at any time (see our <a href="/privacy">privacy policy</a>).</li>
              </ul>
            ),
          },
          {
            title: "Fair use",
            body: (
              <p>
                Please don&apos;t scrape or copy the service at scale, overload it,
                try to break its security, or use it to break the law. We may limit
                or suspend access that does.
              </p>
            ),
          },
          {
            title: "Availability",
            body: (
              <p>
                OptiMiles is provided free and &quot;as is&quot;. We may change,
                pause or stop any part of it, and we don&apos;t guarantee it will
                always be available or error-free.
              </p>
            ),
          },
          {
            title: "Liability",
            body: (
              <p>
                To the extent the law allows, OptiMiles is not liable for losses
                arising from use of the service or reliance on its figures — including
                missed rewards, fees or changed award prices.
              </p>
            ),
          },
          {
            title: "Trademarks",
            body: (
              <p>
                Card, bank, airline and hotel programme names belong to their owners
                and are used only to identify them.
              </p>
            ),
          },
          {
            title: "Changes, law and contact",
            body: (
              <p>
                We may update these terms and will change the date at the top when we
                do. They are governed by the laws of India. Questions:{" "}
                <a href={`mailto:${CONTACT}`}>{CONTACT}</a>.
              </p>
            ),
          },
        ]}
      />
      <SiteFooter />
    </main>
  );
}
