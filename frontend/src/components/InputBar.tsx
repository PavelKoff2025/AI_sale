import { useState, type KeyboardEvent } from "react";
import { defaultConfig } from "../utils/config";

interface InputBarProps {
  onSend: (message: string) => void;
  isLoading: boolean;
  onLeadClick: () => void;
}

export function InputBar({ onSend, isLoading, onLeadClick }: InputBarProps) {
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (input.trim() && !isLoading) {
      onSend(input.trim());
      setInput("");
    }
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t border-gray-200 px-3 py-2 space-y-2">
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={defaultConfig.placeholder}
          disabled={isLoading}
          className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-full focus:outline-none focus:border-blue-500 disabled:opacity-50"
          aria-label="Сообщение"
        />
        <button
          onClick={handleSend}
          disabled={isLoading || !input.trim()}
          className="w-9 h-9 flex items-center justify-center bg-blue-600 text-white rounded-full hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
          aria-label="Отправить"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        </button>
      </div>
      <button
        onClick={onLeadClick}
        className="w-full py-1.5 text-xs text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-lg transition-colors font-medium"
      >
        📞 Оставить заявку — перезвоним за 5 минут
      </button>
    </div>
  );
}
