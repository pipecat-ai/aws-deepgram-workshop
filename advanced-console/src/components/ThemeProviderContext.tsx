import { createContext } from "react";
import type { Theme } from "@pipecat-ai/voice-ui-kit";

type ThemeProviderState = {
  resolvedTheme: "dark" | "light";
  theme: Theme;
  setTheme: (theme: Theme) => void;
};

const initialState: ThemeProviderState = {
  resolvedTheme: "light",
  theme: "system",
  setTheme: () => null,
};

export const ThemeProviderContext =
  createContext<ThemeProviderState>(initialState);
