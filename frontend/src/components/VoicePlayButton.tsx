import { useCallback, useRef, useState } from "react";
import { fetchSpeechAudio } from "../utils/api";

let sharedAudio: HTMLAudioElement | null = null;
let sharedUrl: string | null = null;

function stopShared() {
  if (sharedAudio) {
    sharedAudio.pause();
    sharedAudio = null;
  }
  if (sharedUrl) {
    URL.revokeObjectURL(sharedUrl);
    sharedUrl = null;
  }
}

interface VoicePlayButtonProps {
  text: string;
}

export function VoicePlayButton({ text }: VoicePlayButtonProps) {
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mySession = useRef(0);

  const onClick = useCallback(async () => {
    setError(null);
    if (playing && sharedAudio) {
      stopShared();
      setPlaying(false);
      return;
    }

    stopShared();
    setLoading(true);
    mySession.current += 1;
    const session = mySession.current;

    try {
      const blob = await fetchSpeechAudio(text);
      if (session !== mySession.current) return;

      const url = URL.createObjectURL(blob);
      sharedUrl = url;
      const audio = new Audio(url);
      sharedAudio = audio;

      audio.onended = () => {
        stopShared();
        setPlaying(false);
      };
      audio.onerror = () => {
        stopShared();
        setPlaying(false);
        setError("Ошибка воспроизведения");
      };

      await audio.play();
      setPlaying(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Озвучка недоступна");
    } finally {
      if (session === mySession.current) setLoading(false);
    }
  }, [playing, text]);

  return (
    <div className="mt-1 flex items-center gap-1">
      <button
        type="button"
        onClick={onClick}
        disabled={loading}
        className="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50 flex items-center gap-0.5"
        aria-label={playing ? "Остановить" : "Прослушать ответ"}
      >
        {loading ? (
          <span className="inline-block w-3 h-3 border border-blue-600 border-t-transparent rounded-full animate-spin" />
        ) : playing ? (
          <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M6 6h12v12H6z" />
          </svg>
        ) : (
          <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z" />
          </svg>
        )}
        <span>{loading ? "…" : playing ? "Стоп" : "Слушать"}</span>
      </button>
      {error && <span className="text-[10px] text-red-500">{error}</span>}
    </div>
  );
}
