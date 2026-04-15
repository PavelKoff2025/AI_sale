import type { Message } from "../utils/types";
import { TypingIndicator } from "./TypingIndicator";
import { VoicePlayButton } from "./VoicePlayButton";

interface MessageItemProps {
  message: Message;
}

function isSafeUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

function renderMessageContent(text: string) {
  const parts: (string | JSX.Element)[] = [];
  const combinedRegex = /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|\*\*(.+?)\*\*/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let keyIdx = 0;

  while ((match = combinedRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    if (match[2] !== undefined) {
      const href = match[2];
      if (isSafeUrl(href)) {
        parts.push(
          <a
            key={keyIdx++}
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-brand-500 underline hover:text-brand-700"
          >
            {match[1]}
          </a>
        );
      } else {
        parts.push(match[1]);
      }
    } else if (match[3] !== undefined) {
      parts.push(<strong key={keyIdx++}>{match[3]}</strong>);
    }

    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts;
}

export function MessageItem({ message }: MessageItemProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <img src="/logo-gk.png" alt="ГК" className="w-6 h-6 rounded-full object-cover bg-white mr-2 mt-1 shrink-0" />
      )}
      <div
        className={`max-w-[75%] px-3 py-2 rounded-2xl text-sm leading-relaxed ${
          isUser
            ? "bg-brand-600 text-white rounded-br-sm"
            : "bg-gray-100 text-gray-800 rounded-bl-sm"
        }`}
      >
        {isUser ? message.content : renderMessageContent(message.content)}
        {message.isStreaming && !message.content && <TypingIndicator />}
        {!isUser && message.content && !message.isStreaming && (
          <VoicePlayButton text={message.content} />
        )}
      </div>
    </div>
  );
}
