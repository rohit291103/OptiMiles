import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { ShieldCheck } from "lucide-react";

import { Badge } from "./badge";

const meta = {
  title: "UI/Badge",
  component: Badge,
  tags: ["autodocs"],
  argTypes: {
    variant: {
      control: "select",
      options: [
        "default",
        "secondary",
        "destructive",
        "outline",
        "ghost",
        "link",
      ],
    },
    asChild: { table: { disable: true } },
  },
  args: { children: "Explainable", variant: "default" },
} satisfies Meta<typeof Badge>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Secondary: Story = { args: { variant: "secondary" } };
export const Outline: Story = { args: { variant: "outline" } };

export const Gold: Story = {
  name: "Gold accent",
  args: {
    className: "bg-gold/15 text-gold ring-1 ring-gold/25",
    children: "High confidence",
  },
};

export const WithIcon: Story = {
  args: {
    variant: "outline",
    children: (
      <>
        <ShieldCheck /> Verified
      </>
    ),
  },
};

export const AllVariants: Story = {
  render: () => (
    <div className="flex flex-wrap items-center gap-2">
      <Badge>Default</Badge>
      <Badge variant="secondary">Secondary</Badge>
      <Badge variant="destructive">Destructive</Badge>
      <Badge variant="outline">Outline</Badge>
      <Badge className="bg-gold/15 text-gold ring-1 ring-gold/25">Gold</Badge>
    </div>
  ),
};
