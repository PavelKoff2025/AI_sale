import { useState, useCallback } from "react";
import type { Message } from "../utils/types";
import { streamMessage } from "../utils/api";
import { useSession } from "./useSession";

function uid(): string {
  try {
    return crypto.randomUUID();
  } catch {
    return Math.random().toString(36).slice(2) + Date.now().toString(36);
  }
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { sessionId } = useSession();

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return;

      const userMessage: Message = {
        id: uid(),
        role: "user",
        content: text,
        timestamp: Date.now(),
      };

      const assistantMessage: Message = {
        id: uid(),
        role: "assistant",
        content: "",
        timestamp: Date.now(),
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setIsLoading(true);
      setError(null);

      try {
        let fullContent = "";
        for await (const chunk of streamMessage({
          message: text,
          session_id: sessionId,
        })) {
          fullContent += chunk;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMessage.id
                ? { ...m, content: fullContent }
                : m
            )
          );
        }

        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMessage.id ? { ...m, isStreaming: false } : m
          )
        );
      } catch (err) {
        setError(err instanceof Error ? err.message : "Произошла ошибка");
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMessage.id
              ? {
                  ...m,
                  content: "Извините, произошла ошибка. Попробуйте позже.",
                  isStreaming: false,
                }
              : m
          )
        );
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, sessionId]
  );

  const clearHistory = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return { messages, isLoading, error, sendMessage, clearHistory };
}
