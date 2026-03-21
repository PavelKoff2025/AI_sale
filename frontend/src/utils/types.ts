export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  sources?: Source[];
  isStreaming?: boolean;
}

export interface Source {
  title: string;
  chunk_id: string;
  score: number;
}

export interface ChatRequest {
  message: string;
  session_id: string;
  metadata?: Record<string, string>;
}

export interface ChatResponse {
  session_id: string;
  message: string;
  sources: Source[];
  intent: string;
  tokens_used: number;
}

export interface WidgetConfig {
  apiUrl: string;
  wsUrl: string;
  title: string;
  subtitle: string;
  primaryColor: string;
  position: "bottom-right" | "bottom-left";
  greeting: string;
  placeholder: string;
}
