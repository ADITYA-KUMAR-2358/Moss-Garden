const FILES = {
  "plant-brush": "/audio/plant-brush.mp3",
  sprout: "/audio/sprout.mp3",
  "level-up": "/audio/level-up.mp3",
  badge: "/audio/badge.mp3",
  "xp-drop": "/audio/xp-drop.mp3",
  drought: "/audio/drought.mp3",
  comeback: "/audio/comeback.mp3",
  "card-saved": "/audio/card-saved.mp3",
  "ambient-spring": "/audio/ambient-spring.mp3",
  "ambient-autumn": "/audio/ambient-autumn.mp3",
  "ambient-winter": "/audio/ambient-winter.mp3",
  rain: "/audio/rain.mp3",
  music: "/audio/bg-music.mp3",
};

const LOOPS = new Set(["ambient-spring", "ambient-autumn", "ambient-winter", "rain", "music"]);
const VOLUME_KEYS = {
  master: "moss-vol-master",
  music: "moss-vol-music",
  effects: "moss-vol-effects",
  ambient: "moss-vol-ambient",
};
const STORAGE_KEY = "moss-audio";
const XP_KEY = "moss-xp-heard";
const VISIT_KEY = "moss-last-visit";
const FADE_MS = 2000;
const HOVER_GAP_MS = 400;

const clips = {};
let enabled = false;
let unlocked = false;
let lastHover = 0;
let activeEffect = null;
const queue = [];
const playedOnce = new Set();
let currentBed = null;
let rainClip = null;
let musicClip = null;
const volumes = {
  master: readVolume(VOLUME_KEYS.master, 0.8),
  music: readVolume(VOLUME_KEYS.music, 0.55),
  effects: readVolume(VOLUME_KEYS.effects, 0.85),
  ambient: readVolume(VOLUME_KEYS.ambient, 0.6),
};

function readVolume(key, fallback) {
  const raw = localStorage.getItem(key);
  if (raw === null) return fallback;
  const value = Number(raw);
  if (Number.isNaN(value)) return fallback;
  return Math.min(1, Math.max(0, value));
}

function effectGain() {
  return volumes.master * volumes.effects;
}

function musicGain() {
  return volumes.master * volumes.music * 0.28;
}

function ambientGain() {
  return volumes.master * volumes.ambient * 0.22;
}
const scene = { season: null, level: 0, springLevel: null, rainLevel: null };
let visitNoted = false;

function motionReduced() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function load(name) {
  if (!clips[name]) {
    const audio = new Audio(FILES[name]);
    audio.preload = "auto";
    clips[name] = audio;
  }
  return clips[name];
}

function preload() {
  Object.keys(FILES).forEach(load);
}

function stopClip(audio) {
  if (!audio) return;
  audio._fade = null;
  audio.pause();
  audio.currentTime = 0;
}

function fade(audio, to, ms) {
  const from = audio.volume;
  const token = {};
  audio._fade = token;
  const start = performance.now();
  function step(now) {
    if (audio._fade !== token) return;
    const t = Math.min(1, (now - start) / ms);
    audio.volume = from + (to - from) * t;
    if (t < 1) requestAnimationFrame(step);
    else if (to === 0) audio.pause();
  }
  requestAnimationFrame(step);
}

function bedFor() {
  if (scene.springLevel == null || scene.rainLevel == null) return null;
  if (scene.season === "rain" && scene.level >= scene.springLevel) return "ambient-spring";
  if (scene.season === "leaf") return "ambient-autumn";
  if (scene.season === "frost") return "ambient-winter";
  return null;
}

function stopAmbient() {
  if (currentBed && clips[currentBed]) stopClip(clips[currentBed]);
  currentBed = null;
  if (rainClip) stopClip(rainClip);
}

function syncAmbient() {
  if (!enabled || !unlocked || motionReduced()) {
    stopAmbient();
    return;
  }
  const bed = bedFor();
  if (bed !== currentBed) {
    if (currentBed && clips[currentBed]) fade(clips[currentBed], 0, FADE_MS);
    currentBed = bed;
    if (bed) {
      const audio = load(bed);
      audio.loop = true;
      audio.volume = 0;
      audio.play().catch(() => {});
      fade(audio, ambientGain(), FADE_MS);
    }
  }
  const wantRain = scene.rainLevel != null && scene.level >= scene.rainLevel && ambientGain() > 0;
  if (wantRain) {
    rainClip = load("rain");
    rainClip.loop = true;
    if (rainClip.paused) {
      rainClip.volume = 0;
      rainClip.play().catch(() => {});
    }
    fade(rainClip, ambientGain() * 0.85, FADE_MS);
  } else if (rainClip && !rainClip.paused) {
    fade(rainClip, 0, FADE_MS);
  }
}

function syncMusic() {
  if (!enabled || !unlocked || musicGain() <= 0) {
    if (musicClip && !musicClip.paused) fade(musicClip, 0, FADE_MS);
    return;
  }
  musicClip = load("music");
  musicClip.loop = true;
  if (musicClip.paused) {
    musicClip.volume = 0;
    musicClip.play().catch(() => {});
    fade(musicClip, musicGain(), FADE_MS);
  } else {
    musicClip.volume = musicGain();
  }
}

function applyVolumes() {
  if (musicClip && !musicClip.paused) musicClip.volume = musicGain();
  if (currentBed && clips[currentBed] && !clips[currentBed].paused) clips[currentBed].volume = ambientGain();
  if (rainClip && !rainClip.paused) rainClip.volume = ambientGain() * 0.85;
  if (activeEffect && !activeEffect.paused) activeEffect.volume = effectGain();
}

function effectPlaying() {
  return Boolean(activeEffect && !activeEffect.paused && !activeEffect.ended);
}

function pump() {
  if (!enabled || !unlocked || effectPlaying() || !queue.length) return;
  startEffect(queue.shift());
}

function startEffect(name) {
  if (activeEffect && activeEffect !== clips[name]) stopClip(activeEffect);
  const audio = load(name);
  audio.loop = false;
  audio.volume = effectGain();
  audio.currentTime = 0;
  activeEffect = audio;
  audio.onended = () => {
    if (activeEffect === audio) activeEffect = null;
    pump();
  };
  audio.play().catch(() => {});
}

function play(name) {
  if (!enabled || !FILES[name] || LOOPS.has(name)) return;
  if (name === "plant-brush") {
    if (!unlocked) return;
    const now = Date.now();
    if (now - lastHover < HOVER_GAP_MS) return;
    lastHover = now;
    if (effectPlaying() || queue.length) return;
    startEffect(name);
    return;
  }
  if (!queue.includes(name)) queue.push(name);
  pump();
}

function playOnce(name, key) {
  if (playedOnce.has(key)) return;
  playedOnce.add(key);
  play(name);
}

function playBlob(blob) {
  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);
  audio.preload = "auto";
  if (activeEffect) stopClip(activeEffect);
  queue.length = 0;
  activeEffect = audio;
  audio.volume = effectGain();
  audio.onended = () => {
    if (activeEffect === audio) activeEffect = null;
    URL.revokeObjectURL(url);
  };
  audio.play().catch(() => {});
}

function setEnabled(next) {
  enabled = Boolean(next);
  localStorage.setItem(STORAGE_KEY, enabled ? "on" : "off");
  unlocked = true;
  if (!enabled) {
    if (musicClip) fade(musicClip, 0, 200);
    stopAmbient();
    if (activeEffect) stopClip(activeEffect);
    queue.length = 0;
    return;
  }
  preload();
  syncMusic();
  syncAmbient();
  pump();
}

function restoreAudioPreference() {
  enabled = localStorage.getItem(STORAGE_KEY) === "on";
  unlocked = false;
  return enabled;
}

function armGesture() {
  const release = () => {
    window.removeEventListener("pointerdown", release);
    if (!enabled || unlocked) return;
    unlocked = true;
    preload();
    syncMusic();
    syncAmbient();
    pump();
  };
  window.addEventListener("pointerdown", release);
}

function setScene(next) {
  scene.level = next.level || 0;
  scene.springLevel = next.springLevel;
  scene.rainLevel = next.rainLevel;
  syncAmbient();
}

function setAmbient(season) {
  scene.season = season;
  syncAmbient();
}

function noteXp(xp) {
  const previous = localStorage.getItem(XP_KEY);
  if (previous === null || Number(previous) >= xp || !enabled) {
    if (previous === null || Number(previous) < xp) localStorage.setItem(XP_KEY, String(xp));
    return;
  }
  play("xp-drop");
  localStorage.setItem(XP_KEY, String(xp));
}

function noteVisit(gapDays) {
  if (visitNoted) return false;
  visitNoted = true;
  const today = new Date().toISOString().slice(0, 10);
  const last = localStorage.getItem(VISIT_KEY);
  localStorage.setItem(VISIT_KEY, today);
  if (!last || !gapDays) return false;
  const elapsed = Math.round((Date.parse(today) - Date.parse(last)) / 86400000);
  return elapsed >= gapDays;
}

function setVolume(bus, value) {
  if (!VOLUME_KEYS[bus]) return volumes;
  volumes[bus] = Math.min(1, Math.max(0, Number(value) || 0));
  localStorage.setItem(VOLUME_KEYS[bus], String(volumes[bus]));
  applyVolumes();
  syncMusic();
  syncAmbient();
  return { ...volumes };
}

function currentVolumes() {
  return { ...volumes };
}

export const Sound = {
  play,
  playOnce,
  playBlob,
  setEnabled,
  setAmbient,
  setScene,
  setVolume,
  volumes: currentVolumes,
  restoreAudioPreference,
  armGesture,
  noteXp,
  noteVisit,
  motionReduced,
};
