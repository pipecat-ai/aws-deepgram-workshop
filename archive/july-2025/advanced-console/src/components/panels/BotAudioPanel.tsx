import {
  Panel,
  PanelContent,
  PanelHeader,
  PanelTitle,
} from "@pipecat-ai/voice-ui-kit";
import { MicOffIcon } from "@pipecat-ai/voice-ui-kit";
import {
  usePipecatClientMediaTrack,
  VoiceVisualizer,
} from "@pipecat-ai/client-react";
import { useEffect, useRef, useState } from "react";

interface BotAudioPanelProps {
  audioTracks?: MediaStreamTrack[];
  className?: string;
  collapsed?: boolean;
  visualization?: "bar" | "circle";
  isMuted?: boolean;
  onMuteToggle?: () => void;
}

const barCount = 10;

export const BotAudioPanel: React.FC<BotAudioPanelProps> = ({
  className,
  collapsed = false,
}) => {
  const track = usePipecatClientMediaTrack("audio", "bot");

  const [maxHeight, setMaxHeight] = useState(48);
  const [width, setWidth] = useState(4);

  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;

        const maxWidth = 240;
        const maxBarWidth = maxWidth / (2 * barCount - 1);
        const maxMaxHeight = 240 / (16 / 9);

        const barWidth = Math.max(
          Math.min(width / (barCount * 2), maxBarWidth),
          2
        );
        const maxHeight = Math.max(Math.min(height, maxMaxHeight), 20);

        setMaxHeight(maxHeight);
        setWidth(barWidth);
      }
    });
    observer.observe(containerRef.current);
    return () => {
      observer.disconnect();
    };
  }, []);

  return (
    <Panel className={className}>
      {!collapsed && (
        <PanelHeader>
          <PanelTitle>Bot Audio</PanelTitle>
        </PanelHeader>
      )}
      <PanelContent className="vkui:overflow-hidden">
        <div
          ref={containerRef}
          className="vkui:relative vkui:aspect-video vkui:flex vkui:max-h-full vkui:overflow-hidden"
        >
          <div className="vkui:m-auto">
            <VoiceVisualizer
              participantType="bot"
              backgroundColor="transparent"
              barColor="#ad46ff"
              barCount={barCount}
              barGap={width}
              barLineCap="square"
              barMaxHeight={maxHeight}
              barOrigin="bottom"
              barWidth={width}
            />
          </div>
          {!track && (
            <div className="vkui:absolute vkui:inset-0 vkui:flex vkui:gap-1 vkui:items-center vkui:justify-center">
              <MicOffIcon size={16} />
              {!collapsed && (
                <span className="vkui:font-mono vkui:text-xs">No audio</span>
              )}
            </div>
          )}
        </div>
      </PanelContent>
    </Panel>
  );
};

export default BotAudioPanel;
