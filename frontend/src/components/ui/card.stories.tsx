import type { Meta, StoryObj } from "@storybook/nextjs-vite";

import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "./card";
import { Badge } from "./badge";
import { Button } from "./button";

const meta = {
  title: "UI/Card",
  component: Card,
  tags: ["autodocs"],
  parameters: { layout: "centered" },
} satisfies Meta<typeof Card>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <Card className="w-80">
      <CardHeader>
        <CardTitle>HDFC Infinia</CardTitle>
        <CardDescription>
          Best routed for travel and dining spend.
        </CardDescription>
        <CardAction>
          <Badge className="bg-gold/15 text-gold ring-1 ring-gold/25">
            Top pick
          </Badge>
        </CardAction>
      </CardHeader>
      <CardContent className="text-muted-foreground">
        Route grocery, travel, and online spend here to hit the milestone before
        your goal date.
      </CardContent>
      <CardFooter>
        <Button
          size="sm"
          className="bg-gold text-gold-foreground hover:bg-gold/90"
        >
          See strategy
        </Button>
      </CardFooter>
    </Card>
  ),
};

export const Compact: Story = {
  render: () => (
    <Card size="sm" className="w-72">
      <CardHeader>
        <CardTitle>Projected miles</CardTitle>
        <CardDescription>KrisFlyer, after transfer</CardDescription>
      </CardHeader>
      <CardContent>
        <p className="font-heading text-3xl text-foreground">92,000</p>
        <p className="mt-1 text-xs text-gold">Ready in 11 months</p>
      </CardContent>
    </Card>
  ),
};
