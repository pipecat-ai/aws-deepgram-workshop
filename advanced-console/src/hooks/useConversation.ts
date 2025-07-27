import { RTVIEvent } from "@pipecat-ai/client-js";
import { useRTVIClientEvent } from "@pipecat-ai/client-react";
import { useRef, useState } from "react";

interface ConversationMessage {
  role: "user" | "assistant" | "specialist (thinking)" | "specialist";
  content: string;
  final?: boolean;
  createdAt: string;
  updatedAt?: string;
}

interface Props {
  onMessageAdded?: (message: ConversationMessage) => void;
}

const sortByCreatedAt = (
  a: ConversationMessage,
  b: ConversationMessage
): number => {
  return new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
};

const filterEmptyMessages = (
  message: ConversationMessage,
  index: number,
  array: ConversationMessage[]
): boolean => {
  if (message.content) return true;

  // For empty messages, check if there's a non-empty message with the same role following it
  const nextMessageWithSameRole = array
    .slice(index + 1)
    .find((m) => m.role === message.role && m.content);

  return !nextMessageWithSameRole;
};

export const useConversation = ({ onMessageAdded }: Props = {}) => {
  const [messages, setMessages] = useState<ConversationMessage[]>([]);

  useRTVIClientEvent(RTVIEvent.Connected, () => {
    setMessages([]);
  });

  useRTVIClientEvent(RTVIEvent.BotLlmStarted, () => {
    const now = new Date();
    setMessages((prev) => {
      const lastBotMessageIndex = prev.findLastIndex(
        (msg) => msg.role === "assistant"
      );
      const lastBotMessage = prev[lastBotMessageIndex];
      if (
        lastBotMessage &&
        lastBotMessage.role === "assistant" &&
        !lastBotMessage.content
      ) {
        return prev.sort(sortByCreatedAt).filter(filterEmptyMessages);
      }
      const newMessage: ConversationMessage = {
        role: "assistant",
        content: "",
        final: false,
        createdAt: now.toISOString(),
        updatedAt: now.toISOString(),
      };
      onMessageAdded?.(newMessage);
      return [...prev, newMessage]
        .sort(sortByCreatedAt)
        .filter(filterEmptyMessages);
    });
  });

  useRTVIClientEvent(RTVIEvent.BotLlmText, (data) => {
    const now = new Date();
    setMessages((prev) => {
      const lastBotMessageIndex = prev.findLastIndex(
        (msg) => msg.role === "assistant"
      );
      const lastBotMessage = prev[lastBotMessageIndex];

      if (!lastBotMessage) {
        const newMessage: ConversationMessage = {
          role: "assistant",
          content: data.text,
          createdAt: now.toISOString(),
          updatedAt: now.toISOString(),
        };
        onMessageAdded?.(newMessage);
        return [...prev, newMessage]
          .sort(sortByCreatedAt)
          .filter(filterEmptyMessages);
      }

      // Bump potential empty last message
      if (!lastBotMessage.content) {
        const newMessages = prev.slice();
        newMessages.splice(lastBotMessageIndex, 1, {
          ...lastBotMessage,
          content: data.text,
          createdAt: now.toISOString(),
          updatedAt: now.toISOString(),
        });
        return newMessages.sort(sortByCreatedAt).filter(filterEmptyMessages);
      }

      const isRecent =
        lastBotMessage &&
        lastBotMessage.role === "assistant" &&
        now.getTime() - new Date(lastBotMessage.createdAt).getTime() < 10000; // 10 seconds threshold

      if (isRecent) {
        const newMessages = prev.slice();
        newMessages.splice(lastBotMessageIndex, 1, {
          ...lastBotMessage,
          content: lastBotMessage.content + data.text,
          createdAt: lastBotMessage.content
            ? lastBotMessage.createdAt
            : now.toISOString(),
          updatedAt: now.toISOString(),
        });
        return newMessages.sort(sortByCreatedAt).filter(filterEmptyMessages);
      }

      const newMessage: ConversationMessage = {
        role: "assistant",
        content: data.text,
        createdAt: now.toISOString(),
        updatedAt: now.toISOString(),
      };

      onMessageAdded?.(newMessage);
      return [...prev, newMessage]
        .sort(sortByCreatedAt)
        .filter(filterEmptyMessages);
    });
  });

  useRTVIClientEvent(RTVIEvent.BotLlmStopped, () => {
    setMessages((prev) => {
      const lastBotMessageIndex = prev.findLastIndex(
        (msg) => msg.role === "assistant"
      );
      const lastBotMessage = prev[lastBotMessageIndex];
      if (!lastBotMessage) return prev;
      if (
        lastBotMessage &&
        lastBotMessage.role === "assistant" &&
        !lastBotMessage.content
      ) {
        return prev
          .slice(0, -1)
          .sort(sortByCreatedAt)
          .filter(filterEmptyMessages);
      }
      lastBotMessage.final = true;
      const newMessages = prev.slice();
      newMessages.splice(lastBotMessageIndex, 1, {
        ...lastBotMessage,
        updatedAt: new Date().toISOString(),
      });
      onMessageAdded?.(lastBotMessage);
      return newMessages.sort(sortByCreatedAt).filter(filterEmptyMessages);
    });
  });

  const userStoppedTimeout = useRef<ReturnType<typeof setTimeout>>(undefined);

  useRTVIClientEvent(RTVIEvent.UserStartedSpeaking, () => {
    clearTimeout(userStoppedTimeout.current);
    const now = new Date();
    setMessages((prev) => {
      const lastUserMessageIndex = prev.findLastIndex(
        (msg) => msg.role === "user"
      );
      const lastUserMessage = prev[lastUserMessageIndex];
      if (
        lastUserMessage &&
        lastUserMessage.role === "user" &&
        !lastUserMessage.content
      ) {
        const newMessages = prev.slice();
        newMessages.splice(lastUserMessageIndex, 1, {
          ...lastUserMessage,
          createdAt: now.toISOString(),
          updatedAt: now.toISOString(),
        });
        return newMessages.sort(sortByCreatedAt).filter(filterEmptyMessages);
      }
      const newMessage: ConversationMessage = {
        role: "user",
        content: "",
        final: false,
        createdAt: now.toISOString(),
        updatedAt: now.toISOString(),
      };
      onMessageAdded?.(newMessage);
      return [...prev, newMessage]
        .sort(sortByCreatedAt)
        .filter(filterEmptyMessages);
    });
  });

  useRTVIClientEvent(RTVIEvent.UserTranscript, (data) => {
    const now = new Date();
    setMessages((prev) => {
      const lastUserMessageIndex = prev.findLastIndex(
        (msg) => msg.role === "user"
      );
      const lastUserMessage = prev[lastUserMessageIndex];
      if (lastUserMessage && !lastUserMessage.final) {
        const updatedMessage: ConversationMessage = {
          ...lastUserMessage,
          final: data.final,
          content: data.text,
          updatedAt: now.toISOString(),
        };
        onMessageAdded?.(updatedMessage);
        const newMessages = prev.slice();
        newMessages.splice(lastUserMessageIndex, 1, updatedMessage);
        return newMessages.sort(sortByCreatedAt).filter(filterEmptyMessages);
      }
      const newMessage: ConversationMessage = {
        role: "user",
        content: data.text,
        final: data.final,
        createdAt: now.toISOString(),
      };
      onMessageAdded?.(newMessage);
      return [...prev, newMessage]
        .sort(sortByCreatedAt)
        .filter(filterEmptyMessages);
    });
  });

  useRTVIClientEvent(RTVIEvent.UserStoppedSpeaking, () => {
    clearTimeout(userStoppedTimeout.current);
    userStoppedTimeout.current = setTimeout(() => {
      setMessages((prev) => {
        const lastUserMessageIndex = prev.findLastIndex(
          (msg) => msg.role === "user"
        );
        const lastUserMessage = prev[lastUserMessageIndex];

        if (!lastUserMessage || lastUserMessage.content)
          return prev.sort(sortByCreatedAt).filter(filterEmptyMessages);

        const newMessages = prev.slice();
        newMessages.splice(lastUserMessageIndex, 1);
        return newMessages.sort(sortByCreatedAt).filter(filterEmptyMessages);
      });
    }, 5000);
  });

  // Merge messages of the same role that are close in time (within 30 seconds)
  const getMergedMessages = () => {
    const mergedMessages: ConversationMessage[] = [];

    for (let i = 0; i < messages.length; i++) {
      const currentMessage = messages[i];
      const lastMerged = mergedMessages[mergedMessages.length - 1];

      const timeDiff = lastMerged
        ? Math.abs(
            new Date(currentMessage.createdAt).getTime() -
              new Date(lastMerged.createdAt).getTime()
          )
        : Infinity;

      const shouldMerge =
        lastMerged &&
        lastMerged.role === currentMessage.role &&
        timeDiff < 30000; // 30 seconds threshold

      if (shouldMerge) {
        mergedMessages[mergedMessages.length - 1] = {
          ...lastMerged,
          content: `${lastMerged.content} ${currentMessage.content}`,
          updatedAt: currentMessage.updatedAt || currentMessage.createdAt,
          final: currentMessage.final !== false,
        };
      } else {
        mergedMessages.push({ ...currentMessage });
      }
    }

    return mergedMessages;
  };

  // Handle specialist messages from serverMessage events
  useRTVIClientEvent(RTVIEvent.ServerMessage, (data) => {
    const now = new Date();
    if (data["type"] == "specialist-thinking") {
      setMessages((prev) => {
        const newMessage: ConversationMessage = {
          role: "specialist (thinking)",
          content: data.message,
          final: true,
          createdAt: now.toISOString(),
          updatedAt: now.toISOString(),
        };
        onMessageAdded?.(newMessage);
        return [...prev, newMessage]
          .sort(sortByCreatedAt)
          .filter(filterEmptyMessages);
      });
    }
    if (data["type"] == "specialist-talking") {
      setMessages((prev) => {
        const newMessage: ConversationMessage = {
          role: "specialist",
          content: data.message,
          final: true,
          createdAt: now.toISOString(),
          updatedAt: now.toISOString(),
        };
        onMessageAdded?.(newMessage);
        return [...prev, newMessage]
          .sort(sortByCreatedAt)
          .filter(filterEmptyMessages);
      });
    }
  });

  return {
    messages: getMergedMessages(),
  };
};
export default useConversation;
