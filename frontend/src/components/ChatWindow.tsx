import { useState } from "react";
import { useChat } from "../hooks/useChat";
import { Header } from "./Header";
import { MessageList } from "./MessageList";
import { InputBar } from "./InputBar";
import { QuickReplies } from "./QuickReplies";
import { LeadForm } from "./LeadForm";
import { defaultConfig } from "../utils/config";

interface ChatWindowProps {
  onClose: () => void;
}

export function ChatWindow({ onClose }: ChatWindowProps) {
  const { messages, isLoading, sendMessage, sessionId } = useChat();
  const [showLeadForm, setShowLeadForm] = useState(false);

  const displayMessages =
    messages.length === 0
      ? [
          {
            id: "greeting",
            role: "assistant" as const,
            content: defaultConfig.greeting,
            timestamp: Date.now(),
          },
        ]
      : messages;

  const showQuickReplies = messages.length === 0;

  const openLeadForm = () => setShowLeadForm(true);

  const handleSend = (text: string) => {
    sendMessage(text);
  };

  return (
    <div className="w-[380px] h-[520px] bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-gray-200 max-sm:fixed max-sm:inset-0 max-sm:w-full max-sm:h-full max-sm:rounded-none">
      <Header onClose={onClose} onLeadClick={openLeadForm} />

      {showLeadForm ? (
        <LeadForm onClose={() => setShowLeadForm(false)} sessionId={sessionId} />
      ) : (
        <>
          <MessageList messages={displayMessages} />
          <QuickReplies onSelect={handleSend} onLeadClick={openLeadForm} visible={showQuickReplies} />
          <InputBar onSend={handleSend} isLoading={isLoading} onLeadClick={openLeadForm} />
        </>
      )}
    </div>
  );
}
