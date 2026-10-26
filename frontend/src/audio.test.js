import test from "node:test";
import assert from "node:assert/strict";

const storage = new Map();
globalThis.localStorage = {
  getItem: (key) => storage.get(key) ?? null,
  setItem: (key, value) => storage.set(key, String(value)),
  removeItem: (key) => storage.delete(key),
};
globalThis.window = {
  matchMedia: () => ({ matches: false }),
  addEventListener: () => {},
  removeEventListener: () => {},
};
globalThis.performance = { now: () => 0 };
const frames = [];
globalThis.requestAnimationFrame = (callback) => {
  frames.push(callback);
  return frames.length;
};
const instances = [];

class MockAudio {
  constructor(url) {
    this.url = url;
    this.volume = 1;
    this.paused = true;
    this.ended = false;
    this.loop = false;
    this.playCount = 0;
    instances.push(this);
  }

  play() {
    this.paused = false;
    this.ended = false;
    this.playCount += 1;
    return Promise.resolve();
  }

  pause() {
    this.paused = true;
  }
}

globalThis.Audio = MockAudio;
globalThis.URL = {
  createObjectURL: () => "blob:test",
  revokeObjectURL: () => {},
};

const { Sound } = await import("./audio.js");

test("music resumes after sound is toggled off during a fade", () => {
  Sound.setEnabled(true);
  Sound.armGesture();
  window.dispatchEvent?.(new Event("pointerdown"));
  Sound.setVolume("music", 1);
  Sound.setEnabled(false);
  Sound.setEnabled(true);
  frames.splice(0).forEach((frame) => frame(2000));

  assert.equal(Sound.volumes().music, 1);
  assert.equal(storage.get("moss-audio"), "on");
  const music = instances.find((audio) => audio.url === "/audio/bg-music.mp3");
  assert.equal(music.loop, true);
  assert.equal(music.paused, false);
});

test("background music is configured to loop", () => {
  Sound.setEnabled(true);
  Sound.setVolume("music", 0.8);
  assert.equal(storage.get("moss-audio"), "on");
  assert.equal(instances.find((audio) => audio.url === "/audio/bg-music.mp3").loop, true);
});
