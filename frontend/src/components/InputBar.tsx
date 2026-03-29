import { useRef, useState, type ChangeEvent, type KeyboardEvent } from "react";
import { defaultConfig } from "../utils/config";
import { useVoiceRecorder } from "../hooks/useVoiceRecorder";
import { transcribeVoice } from "../utils/api";

interface InputBarProps {
  onSend: (message: string) => void;
  isLoading: boolean;
  onLeadClick: () => void;
}

export function InputBar({ onSend, isLoading, onLeadClick }: InputBarProps) {
  const [input, setInput] = useState("");
  const [isSecureContext] = useState(
    () => typeof window !== "undefined" && window.isSecureContext
  );
  const [fileVoiceBusy, setFileVoiceBusy] = useState(false);
  const [fileVoiceError, setFileVoiceError] = useState<string | null>(null);
  const audioFileRef = useRef<HTMLInputElement>(null);

  const { state, voiceError, clearVoiceError, toggleRecording, isVoiceBusy } =
    useVoiceRecorder(onSend);

  const voiceBusy = isVoiceBusy || fileVoiceBusy;
  const displayError = voiceError || fileVoiceError;

  const handleAudioFile = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || isLoading) return;
    setFileVoiceError(null);
    clearVoiceError();
    setFileVoiceBusy(true);
    try {
      const text = await transcribeVoice(file);
      const trimmed = text.trim();
      if (trimmed) onSend(trimmed);
      else setFileVoiceError("Речь не распознана, попробуйте другой файл");
    } catch (err) {
      setFileVoiceError(err instanceof Error ? err.message : "Ошибка распознавания");
    } finally {
      setFileVoiceBusy(false);
    }
  };

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

  const micDisabled = isLoading || voiceBusy;

  return (
    <div className="border-t border-gray-200 px-3 py-2 space-y-2">
      <input
        ref={audioFileRef}
        type="file"
        accept="audio/*,.mp3,.m4a,.wav,.webm,.ogg,.flac"
        className="hidden"
        aria-hidden
        onChange={handleAudioFile}
      />
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => {
            clearVoiceError();
            setFileVoiceError(null);
            setInput(e.target.value);
          }}
          onKeyDown={handleKeyDown}
          placeholder={defaultConfig.placeholder}
          disabled={isLoading || voiceBusy}
          className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-full focus:outline-none focus:border-blue-500 disabled:opacity-50"
          aria-label="Сообщение"
        />
        {isSecureContext ? (
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
        ) : (
          <button
            type="button"
            onClick={() => audioFileRef.current?.click()}
            disabled={micDisabled}
            title="Выберите аудиофайл с записью (mp3, m4a, webm…)"
            className="w-9 h-9 flex items-center justify-center rounded-full bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Загрузить голосовой файл"
          >
            {fileVoiceBusy ? (
              <span className="inline-block w-4 h-4 border-2 border-gray-500 border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
              </svg>
            )}
          </button>
        )}
        <button
          onClick={handleSend}
          disabled={isLoading || !input.trim() || voiceBusy}
          className="w-9 h-9 flex items-center justify-center bg-blue-600 text-white rounded-full hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
          aria-label="Отправить"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        </button>
      </div>
      {!isSecureContext && (
        <p className="text-[10px] text-gray-500 text-center px-1 leading-snug">
          Без HTTPS микрофон в браузере недоступен. Нажмите скрепку и выберите аудиофайл
          (запись с телефона или диктофона: mp3, m4a, webm).
        </p>
      )}
      {displayError && (
        <p className="text-[11px] text-red-600 text-center px-1">{displayError}</p>
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
