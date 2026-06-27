import type { Meta, StoryObj } from "@storybook/nextjs-vite";

import { HeroFlow } from "./hero-flow";

const meta = {
  title: "Sections/HeroFlow",
  component: HeroFlow,
  tags: ["autodocs"],
  parameters: { layout: "centered" },
  // HeroFlow has a soft gold glow that extends past the card edges and an
  // entrance animation; give it room to breathe.
  decorators: [
    (Story) => (
      <div className="w-[26rem] max-w-full p-10">
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof HeroFlow>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
