import { useCallback, useEffect, useRef, useState } from "react";
import { transcribeVoice } from "../utils/api";

export type VoiceRecorderState = "idle" | "recording" | "processing" | "error";

function pickMimeType(): string {
  const types = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
  ];
  for (const t of types) {
    if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(t)) {
      return t;
    }
  }
  return "";
}

export function useVoiceRecorder(onTranscript: (text: string) => void) {
  const [state, setState] = useState<VoiceRecorderState>("idle");
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const mediaRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);

  const cleanupStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  const stopRecording = useCallback(async () => {
    const mr = mediaRef.current;
    if (!mr || mr.state === "inactive") return;
    mr.stop();
    mediaRef.current = null;
  }, []);

  const startRecording = useCallback(async () => {
    setVoiceError(null);
    if (typeof window !== "undefined" && !window.isSecureContext) {
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      setVoiceError("Микрофон не поддерживается в этом браузере");
      setState("error");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];
      const mime = pickMimeType();
      const mr = mime
        ? new MediaRecorder(stream, { mimeType: mime })
        : new MediaRecorder(stream);
      mediaRef.current = mr;

      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mr.onerror = () => {
        setVoiceError("Ошибка записи");
        setState("error");
        cleanupStream();
      };

      mr.onstop = async () => {
        cleanupStream();
        const type = mr.mimeType || "audio/webm";
        const blob = new Blob(chunksRef.current, { type });
        chunksRef.current = [];
        if (blob.size < 200) {
          setState("idle");
          return;
        }
        setState("processing");
        try {
          const text = await transcribeVoice(blob);
          const trimmed = text.trim();
          if (trimmed) onTranscript(trimmed);
        } catch (e) {
          setVoiceError(e instanceof Error ? e.message : "Не удалось распознать речь");
          setState("error");
          return;
        }
        setState("idle");
      };

      mr.start(200);
      setState("recording");
    } catch (e) {
      const msg =
        e instanceof Error && e.name === "NotAllowedError"
          ? "Разрешите доступ к микрофону"
          : "Не удалось включить микрофон";
      setVoiceError(msg);
      setState("error");
      cleanupStream();
    }
  }, [cleanupStream, onTranscript]);

  useEffect(() => {
    return () => {
      if (mediaRef.current && mediaRef.current.state !== "inactive") {
        mediaRef.current.stop();
      }
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      mediaRef.current = null;
    };
  }, []);

  const toggleRecording = useCallback(async () => {
    if (state === "recording") {
      await stopRecording();
      return;
    }
    if (state === "processing") return;
    if (state === "error") {
      setState("idle");
      setVoiceError(null);
    }
    await startRecording();
  }, [state, startRecording, stopRecording]);

  return {
    state,
    voiceError,
    clearVoiceError: () => setVoiceError(null),
    toggleRecording,
    isVoiceBusy: state === "recording" || state === "processing",
  };
}
