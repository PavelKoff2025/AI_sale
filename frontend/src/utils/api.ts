import type { ChatRequest, ChatResponse } from "./types";
import { defaultConfig } from "./config";

export async function transcribeVoice(blob: Blob): Promise<string> {
  const fd = new FormData();
  const filename =
    typeof File !== "undefined" && blob instanceof File && blob.name
      ? blob.name
      : "voice.webm";
  fd.append("audio", blob, filename);
  const response = await fetch(`${defaultConfig.apiUrl}/api/voice/transcribe`, {
    method: "POST",
    body: fd,
  });
  if (!response.ok) {
    let msg = `Ошибка ${response.status}`;
    try {
      const err = await response.json();
      if (typeof err.detail === "string") msg = err.detail;
      else if (Array.isArray(err.detail)) msg = err.detail.map((d: { msg?: string }) => d.msg).join(", ");
    } catch {
      /* ignore */
    }
    throw new Error(msg);
  }
  const data = (await response.json()) as { text: string };
  return data.text ?? "";
}

export async function fetchSpeechAudio(text: string): Promise<Blob> {
  const response = await fetch(`${defaultConfig.apiUrl}/api/voice/synthesize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) {
    let msg = `Ошибка ${response.status}`;
    try {
      const err = await response.json();
      if (typeof err.detail === "string") msg = err.detail;
    } catch {
      /* ignore */
    }
    throw new Error(msg);
  }
  return response.blob();
}

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
