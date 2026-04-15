import { useState, useCallback } from "react";
import { ChatWindow } from "./ChatWindow";
import { ChatBubble } from "./ChatBubble";

interface ChatWidgetProps {
  externalOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export function ChatWidget({ externalOpen, onOpenChange }: ChatWidgetProps = {}) {
  const [internalOpen, setInternalOpen] = useState(false);

  const isOpen = externalOpen ?? internalOpen;

  const setOpen = useCallback(
    (v: boolean) => {
      setInternalOpen(v);
      onOpenChange?.(v);
    },
    [onOpenChange],
  );

  return (
    <div className="fixed bottom-6 right-6 z-[9999] flex flex-col items-end gap-4">
      {isOpen && <ChatWindow onClose={() => setOpen(false)} />}
      <ChatBubble isOpen={isOpen} onClick={() => setOpen(!isOpen)} />
    </div>
  );
}
