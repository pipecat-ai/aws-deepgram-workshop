"use client";

import { FullScreenContainer, ThemeProvider } from "@pipecat-ai/voice-ui-kit";

import { ConsoleTemplate } from "@/templates/Console";

export default function Home() {
  return (
    <ThemeProvider>
      <FullScreenContainer>
        <ConsoleTemplate
          transportType="smallwebrtc"
          connectParams={{
            connectionUrl: "/api/offer",
          }}
          noUserVideo={true}
        />
      </FullScreenContainer>
    </ThemeProvider>
  );
}
