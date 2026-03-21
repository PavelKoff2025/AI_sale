import { useState } from "react";
import { ChatWindow } from "./ChatWindow";
import { ChatBubble } from "./ChatBubble";

export function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="fixed bottom-6 right-6 z-[9999] flex flex-col items-end gap-4">
      {isOpen && <ChatWindow onClose={() => setIsOpen(false)} />}
      <ChatBubble isOpen={isOpen} onClick={() => setIsOpen(!isOpen)} />
    </div>
  );
}
