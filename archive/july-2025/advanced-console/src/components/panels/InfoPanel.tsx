import {
  AudioOutput,
  ClientStatus,
  SessionInfo,
  UserAudioControl,
  UserVideoControl,
  Panel,
  PanelContent,
  PanelHeader,
  PanelTitle,
} from "@pipecat-ai/voice-ui-kit";

interface Props {
  noAudioOutput?: boolean;
  noSessionInfo?: boolean;
  noStatusInfo?: boolean;
  noUserAudio?: boolean;
  noUserVideo?: boolean;
  participantId?: string;
  sessionId?: string;
}

export const InfoPanel: React.FC<Props> = ({
  noAudioOutput = false,
  noSessionInfo = false,
  noStatusInfo = false,
  noUserAudio = false,
  noUserVideo = false,
  participantId,
  sessionId,
}) => {
  const noDevices = noAudioOutput && noUserAudio && noUserVideo;
  const noInfoPanel = noStatusInfo && noDevices && noSessionInfo;

  if (noInfoPanel) return null;

  return (
    <Panel className="vkui:h-full vkui:overflow-y-auto vkui:overflow-x-hidden">
      {!noStatusInfo && (
        <>
          <PanelHeader variant="inline">
            <PanelTitle>Status</PanelTitle>
          </PanelHeader>
          <PanelContent>
            <ClientStatus />
          </PanelContent>
        </>
      )}
      {!noDevices && (
        <>
          <PanelHeader
            className="vkui:border-t vkui:border-t-border"
            variant="inline"
          >
            <PanelTitle>Devices</PanelTitle>
          </PanelHeader>
          <PanelContent>
            {!noUserAudio && <UserAudioControl />}
            {!noUserVideo && <UserVideoControl />}
            {!noAudioOutput && <AudioOutput />}
          </PanelContent>
        </>
      )}
      {!noSessionInfo && (
        <>
          <PanelHeader
            className="vkui:border-t vkui:border-t-border"
            variant="inline"
          >
            <PanelTitle>Session</PanelTitle>
          </PanelHeader>
          <PanelContent>
            <SessionInfo sessionId={sessionId} participantId={participantId} />
          </PanelContent>
        </>
      )}
    </Panel>
  );
};

export default InfoPanel;
