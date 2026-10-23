import { useEffect, useState } from "react";

export function canSpeak() {
  return typeof window !== "undefined" && "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
}

function pickVoice() {
  const voices = window.speechSynthesis.getVoices();
  return voices.find((voice) => voice.lang?.startsWith("en") && voice.localService)
    || voices.find((voice) => voice.lang?.startsWith("en"))
    || null;
}

// Plays only after a press, never on load. Stops when the component unmounts.
export function useReadAloud(text) {
  const [speaking, setSpeaking] = useState(false);

  useEffect(() => () => {
    if (canSpeak()) window.speechSynthesis.cancel();
  }, []);

  function toggle() {
    if (!canSpeak() || !text) return;
    const synth = window.speechSynthesis;
    if (speaking) {
      synth.cancel();
      setSpeaking(false);
      return;
    }
    synth.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    const voice = pickVoice();
    if (voice) utterance.voice = voice;
    utterance.rate = 0.95;
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    synth.speak(utterance);
    setSpeaking(true);
  }

  return { speaking, toggle, supported: canSpeak() };
}
