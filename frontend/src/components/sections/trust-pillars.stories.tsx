import type { Meta, StoryObj } from "@storybook/nextjs-vite";

import { TrustPillars } from "./trust-pillars";

const meta = {
  title: "Sections/TrustPillars",
  component: TrustPillars,
  tags: ["autodocs"],
  parameters: { layout: "fullscreen" },
  // The pillars are a responsive 1 / 2 / 4-up grid; the wrapper provides the
  // page gutter and width so the grid breakpoints are exercised.
  decorators: [
    (Story) => (
      <div className="px-6 py-16 sm:px-10 lg:px-16">
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof TrustPillars>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
