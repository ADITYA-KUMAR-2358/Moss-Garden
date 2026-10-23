import { useEffect, useRef, useState } from "react";

export function canSpeak() {
  return typeof window !== "undefined" && "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
}

function pickVoice() {
  const voices = window.speechSynthesis.getVoices();
  return voices.find((voice) => voice.lang?.startsWith("en") && voice.localService)
    || voices.find((voice) => voice.lang?.startsWith("en"))
    || null;
}

// Plays only after a press, never on load. `src` is an ElevenLabs recording; without it, or if it fails
// to load, the browser's own voice reads `text`. Stops when the component unmounts.
export function useNarration({ src, text }) {
  const [state, setState] = useState("idle");
  const [voice, setVoice] = useState(src ? "elevenlabs" : "browser");
  const audio = useRef(null);
  const objectUrl = useRef(null);
  const attempt = useRef(0);

  function release() {
    if (audio.current) {
      audio.current.pause();
      audio.current = null;
    }
    if (objectUrl.current) {
      URL.revokeObjectURL(objectUrl.current);
      objectUrl.current = null;
    }
  }

  function stop() {
    attempt.current += 1;
    audio.current?.pause();
    if (canSpeak()) window.speechSynthesis.cancel();
    setState("idle");
  }

  useEffect(() => {
    setVoice(src ? "elevenlabs" : "browser");
    return () => {
      attempt.current += 1;
      release();
      if (canSpeak()) window.speechSynthesis.cancel();
      setState("idle");
    };
  }, [src, text]);

  function speakInBrowser() {
    if (!canSpeak() || !text) {
      setState("idle");
      return;
    }
    const synth = window.speechSynthesis;
    synth.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    const chosen = pickVoice();
    if (chosen) utterance.voice = chosen;
    utterance.rate = 0.95;
    utterance.onend = () => setState("idle");
    utterance.onerror = () => setState("idle");
    setVoice("browser");
    synth.speak(utterance);
    setState("playing");
  }

  async function toggle() {
    if (state !== "idle") {
      stop();
      return;
    }
    if (!src) {
      speakInBrowser();
      return;
    }
    const mine = attempt.current + 1;
    attempt.current = mine;
    setState("loading");
    try {
      if (!audio.current) {
        const response = await fetch(src);
        if (!response.ok) throw new Error("narration unavailable");
        const blob = await response.blob();
        if (attempt.current !== mine) return;
        objectUrl.current = URL.createObjectURL(blob);
        audio.current = new Audio(objectUrl.current);
        audio.current.onended = () => setState("idle");
      }
      audio.current.currentTime = 0;
      await audio.current.play();
      if (attempt.current !== mine) {
        audio.current?.pause();
        return;
      }
      setVoice("elevenlabs");
      setState("playing");
    } catch {
      if (attempt.current !== mine) return;
      release();
      speakInBrowser();
    }
  }

  return {
    state,
    loading: state === "loading",
    speaking: state === "playing",
    voice,
    toggle,
    supported: Boolean(src) || canSpeak(),
  };
}
