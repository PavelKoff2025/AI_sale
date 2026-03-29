import { useState, type KeyboardEvent } from "react";
import { defaultConfig } from "../utils/config";
import { useVoiceRecorder } from "../hooks/useVoiceRecorder";

interface InputBarProps {
  onSend: (message: string) => void;
  isLoading: boolean;
  onLeadClick: () => void;
}

export function InputBar({ onSend, isLoading, onLeadClick }: InputBarProps) {
  const [input, setInput] = useState("");
  const { state, voiceError, clearVoiceError, toggleRecording, isVoiceBusy } =
    useVoiceRecorder(onSend);

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

  const micDisabled = isLoading || isVoiceBusy;

  return (
    <div className="border-t border-gray-200 px-3 py-2 space-y-2">
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => {
            clearVoiceError();
            setInput(e.target.value);
          }}
          onKeyDown={handleKeyDown}
          placeholder={defaultConfig.placeholder}
          disabled={isLoading || isVoiceBusy}
          className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-full focus:outline-none focus:border-blue-500 disabled:opacity-50"
          aria-label="Сообщение"
        />
        <button
          type="button"
          onClick={() => toggleRecording()}
          disabled={micDisabled}
          title={
            state === "recording"
              ? "Нажмите, чтобы отправить запись"
              : "Голосовое сообщение"
          }
          className={`w-9 h-9 flex items-center justify-center rounded-full transition-colors flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed ${
            state === "recording"
              ? "bg-red-500 text-white animate-pulse"
              : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
          aria-label={state === "recording" ? "Остановить запись" : "Записать голос"}
        >
          {state === "processing" ? (
            <span className="inline-block w-4 h-4 border-2 border-gray-500 border-t-transparent rounded-full animate-spin" />
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
              <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
            </svg>
          )}
        </button>
        <button
          onClick={handleSend}
          disabled={isLoading || !input.trim() || isVoiceBusy}
          className="w-9 h-9 flex items-center justify-center bg-blue-600 text-white rounded-full hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
          aria-label="Отправить"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        </button>
      </div>
      {voiceError && (
        <p className="text-[11px] text-red-600 text-center px-1">{voiceError}</p>
      )}
      <button
        onClick={onLeadClick}
        className="w-full py-1.5 text-xs text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-lg transition-colors font-medium"
      >
        📞 Оставить заявку — перезвоним за 5 минут
      </button>
    </div>
  );
}
