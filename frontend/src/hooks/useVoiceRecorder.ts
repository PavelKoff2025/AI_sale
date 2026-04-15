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
  const onTranscriptRef = useRef(onTranscript);

  useEffect(() => {
    onTranscriptRef.current = onTranscript;
  }, [onTranscript]);

  const cleanupStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    mediaRef.current = null;
  }, []);

  const processBlob = useCallback(async (blob: Blob) => {
    if (blob.size < 200) {
      setState("idle");
      return;
    }
    setState("processing");
    try {
      const text = await transcribeVoice(blob);
      const trimmed = text.trim();
      if (trimmed) {
        onTranscriptRef.current(trimmed);
      } else {
        setVoiceError("Речь не распознана, попробуйте ещё раз");
      }
    } catch (e) {
      setVoiceError(e instanceof Error ? e.message : "Не удалось распознать речь");
    } finally {
      setState("idle");
    }
  }, []);

  const startRecording = useCallback(async () => {
    setVoiceError(null);
    setState("idle");

    if (typeof window !== "undefined" && !window.isSecureContext) {
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      setVoiceError("Микрофон не поддерживается в этом браузере");
      return;
    }
    try {
      cleanupStream();
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
        setState("idle");
        cleanupStream();
      };

      mr.onstop = () => {
        cleanupStream();
        const type = mr.mimeType || "audio/webm";
        const blob = new Blob(chunksRef.current, { type });
        chunksRef.current = [];
        processBlob(blob);
      };

      mr.start(200);
      setState("recording");
    } catch (e) {
      const msg =
        e instanceof Error && e.name === "NotAllowedError"
          ? "Разрешите доступ к микрофону"
          : "Не удалось включить микрофон";
      setVoiceError(msg);
      setState("idle");
      cleanupStream();
    }
  }, [cleanupStream, processBlob]);

  const stopRecording = useCallback(() => {
    const mr = mediaRef.current;
    if (mr && mr.state !== "inactive") {
      mr.stop();
    }
  }, []);

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
      stopRecording();
      return;
    }
    if (state === "processing") return;
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
