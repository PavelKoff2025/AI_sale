import type { WidgetConfig } from "./types";

const resolveWsUrl = (): string => {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL;
  if (typeof window !== "undefined") {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${window.location.host}/ws/chat`;
  }
  return "ws://localhost:8080/ws/chat";
};

export const defaultConfig: WidgetConfig = {
  apiUrl: import.meta.env.VITE_API_URL || "",
  wsUrl: resolveWsUrl(),
  title: "ГК Проект",
  subtitle: "Онлайн-консультант",
  primaryColor: "#3D3D3D",
  position: "bottom-right",
  greeting: "Здравствуйте! Я AI-помощник «ГК Проект». Помогу с вопросами по монтажу котельных, отопления, водоснабжения, электрики и канализации. Чем могу помочь?",
  placeholder: "Задайте вопрос об услугах...",
};
