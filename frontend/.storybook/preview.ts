import type { Preview } from "@storybook/nextjs-vite";

import "../src/app/globals.css";
import "./preview.css";

const preview: Preview = {
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    backgrounds: { disable: true },
    a11y: { test: "todo" },
  },
  // The site is dark-only: render every story inside `.dark` so the gold/dark
  // tokens (which only exist under `.dark` in globals.css) apply. Without this
  // the previews would silently render the unstyled light theme.
  decorators: [
    (Story) => {
      if (typeof document !== "undefined") {
        document.documentElement.classList.add("dark");
        document.body.classList.add("dark", "bg-grain");
      }
      return Story();
    },
  ],
};

export default preview;
