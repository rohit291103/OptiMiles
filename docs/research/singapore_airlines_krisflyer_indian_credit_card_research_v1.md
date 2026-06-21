# /docs/research/indian-travel-rewards-v1.md

## Executive Summary
This document synthesizes current market data for the Indian premium credit card ecosystem, focusing strictly on Singapore Airlines KrisFlyer business-class optimization. It outlines essential transfer ratios, milestone triggers, and the rigid transfer caps recently introduced into the market that OptiMILES must account for in its MVP.

---

## 1. Structured Card Comparison: KrisFlyer Optimization

| Priority Card | Base Reward Earn Rate | KrisFlyer Transfer Ratio | Relevant Annual Capping / Limitations | Annual Fee & Waiver |
| :--- | :--- | :--- | :--- | :--- |
| **HDFC Infinia (Metal)** | ~3.3% (5 RP per ₹150) | 1:1 | 1.5L RP monthly cap on SmartBuy travel | ₹10L spend waiver |
| **HDFC Diners Club Black (Metal)** | ~3.3% (5 RP per ₹150) | 1:1 | 75,000 RP monthly redemption cap | ₹10,000 + GST <br> ₹8L spend waiver |
| **Axis Magnus Burgundy** | ~4.8% effective base rate | 5:4 (5 RP = 4 Miles) | 2,00,000 Group A point transfer cap annually | ₹30,000 + GST |
| **Axis Magnus (Standard)** | Tiered milestones based on spend | 5:2 (5 RP = 2 Miles) | Strict annual caps into Group A and Group B | Varies |
| **Axis Atlas** | Tiered milestone rewards | 1:2 (1 EDGE Mile = 2 Miles) | 30,000 EDGE Miles transfer cap to Group A annually | ₹5,000 + GST |
| **Amex Platinum Travel** | Milestone-driven | 2:1 (2 MR = 1 Mile)* | Requires claiming bonuses manually if earned prior to March 2026 | Varies |

*\*Ratio based on standard Amex India Membership Rewards transfer terms for premium cards.*

---

## 2. Key Optimization Insights & Ecosystem Caveats

*   **Axis Bank Transfer Restrictions**: Axis Bank has separated its airline and hotel partners into two groups (Group A and Group B), which enforces strict annual transfer caps on all its premium products. Singapore Airlines KrisFlyer is assigned to Group A.
*   **The Axis Atlas Bottleneck**: The Axis Atlas card features an excellent 1:2 transfer ratio for KrisFlyer. However, cardholders are hard-capped at transferring a maximum of 30,000 EDGE Miles to Group A partners per calendar year. Because of the 1:2 ratio, this limits Atlas users to accumulating a maximum of 60,000 KrisFlyer miles per year through this specific avenue.
*   **HDFC Stability**: HDFC Bank’s Infinia and Diners Club Black Metal cards remain highly reliable for KrisFlyer redemptions, transferring at a straightforward 1:1 ratio. These cards lack basic transfer milestone bonuses but compensate with high-yield accelerated rewards via the SmartBuy portal, yielding up to 10X points.
*   **Amex Milestone Maximization**: The American Express Platinum Travel provides major utility through its annual milestone system, granting bulk Bonus Membership Rewards points when specific spend thresholds are achieved.

---

## 3. Best Reward Accumulation Strategies

*   **The HDFC SmartBuy Multiplier**: HDFC Infinia cardholders should funnel their travel, voucher, and hotel expenses through the SmartBuy portal to leverage the up to 10X reward multipliers. With an effective reward rate scaling massively on these accelerated categories, combined with a 1:1 KrisFlyer transfer ratio, this forms a stable base for long-haul business class redemptions.
*   **Axis Burgundy Consolidation**: High-net-worth individuals should target the Axis Magnus Burgundy as their primary card. With an effective base rewards rate of 4.8% and a strong 5:4 KrisFlyer transfer ratio, it possesses the highest base earning potential among the major Indian four. Furthermore, it boasts a much higher Group A transfer cap of 2,00,000 points annually.
*   **Amex Milestone Stacking**: For mid-tier spenders, concentrating non-category spend on the Amex Platinum Travel to precisely hit the annual milestone targets is the most mathematically sound approach to building a healthy Membership Rewards balance.

---

## 4. Realistic Recommendations for MVP Support

*   **Hardcode Cap Logic**: The OptiMILES platform must integrate Axis Bank's Group A and Group B transfer limits into its calculation engine to avoid recommending impossible redemptions. 
*   **Dynamic Ratio Matrix**: The MVP must accurately apply Axis Bank’s tiered transfer ratios based on the specific card tier—such as Atlas (1:2), standard Magnus (5:2), and Magnus Burgundy (5:4)—as these significantly alter the final KrisFlyer mile calculation.
*   **Quarterly/Annual Spend Triggers**: For cards like the Amex Platinum Travel and HDFC DCB Metal (which offers 10,000 RP on ₹4L quarterly spend), projecting mile accumulation is impossible without factoring in these milestone bursts. OptiMILES should track user spend against these specific thresholds to accurately forecast reward generation.