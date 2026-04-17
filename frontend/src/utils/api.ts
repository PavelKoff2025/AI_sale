import type { ChatRequest, ChatResponse } from "./types";
import { defaultConfig } from "./config";

let _token: string | null = null;
let _tokenExpiry = 0;

async function getAuthToken(): Promise<string> {
  if (_token && Date.now() < _tokenExpiry) return _token;

  try {
    const res = await fetch(`${defaultConfig.apiUrl}/api/auth/token`, {
      method: "POST",
    });
    if (res.ok) {
      const data = await res.json();
      _token = data.access_token;
      _tokenExpiry = Date.now() + (data.expires_in - 60) * 1000;
      return _token!;
    }
  } catch {
    /* auth endpoint unavailable — proceed without token */
  }
  return "";
}

async function authHeaders(): Promise<Record<string, string>> {
  const token = await getAuthToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

export async function transcribeVoice(blob: Blob): Promise<string> {
  const token = await getAuthToken();
  const fd = new FormData();
  const filename =
    typeof File !== "undefined" && blob instanceof File && blob.name
      ? blob.name
      : "voice.webm";
  fd.append("audio", blob, filename);

  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const response = await fetch(`${defaultConfig.apiUrl}/api/voice/transcribe`, {
    method: "POST",
    headers,
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
  const headers = await authHeaders();
  const response = await fetch(`${defaultConfig.apiUrl}/api/voice/synthesize`, {
    method: "POST",
    headers,
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
  const headers = await authHeaders();
  const response = await fetch(`${defaultConfig.apiUrl}/api/chat`, {
    method: "POST",
    headers,
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

export async function* streamMessage(
  request: ChatRequest,
  signal?: AbortSignal
): AsyncGenerator<string> {
  const headers = await authHeaders();
  const response = await fetch(`${defaultConfig.apiUrl}/api/chat/stream`, {
    method: "POST",
    headers,
    body: JSON.stringify(request),
    signal,
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
