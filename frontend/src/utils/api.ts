import type { ChatRequest, ChatResponse } from "./types";
import { defaultConfig } from "./config";

export async function sendMessage(request: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(`${defaultConfig.apiUrl}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

export async function* streamMessage(
  request: ChatRequest
): AsyncGenerator<string> {
  const response = await fetch(`${defaultConfig.apiUrl}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6);
        if (data === "[DONE]") return;

        try {
          const parsed = JSON.parse(data);
          if (parsed.type === "chunk" && parsed.content) {
            yield parsed.content;
          }
        } catch {
          // skip malformed SSE
        }
      }
    }
  }
}
