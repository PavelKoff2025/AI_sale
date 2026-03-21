import { useState } from "react";

const SESSION_KEY = "ai_sale_session_id";

function generateId(): string {
  try {
    return crypto.randomUUID();
  } catch {
    return "s-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
  }
}

function getOrCreateSessionId(): string {
  const existing = localStorage.getItem(SESSION_KEY);
  if (existing) return existing;

  const newId = generateId();
  localStorage.setItem(SESSION_KEY, newId);
  return newId;
}

export function useSession() {
  const [sessionId] = useState(getOrCreateSessionId);

  const resetSession = () => {
    const newId = generateId();
    localStorage.setItem(SESSION_KEY, newId);
    window.location.reload();
  };

  return { sessionId, resetSession };
}
