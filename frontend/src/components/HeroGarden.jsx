import { useEffect, useState } from "react";
import { gardenLayers } from "../art/gardenLayers.js";
import { levelName } from "./Dashboard.jsx";

// The layer art spans x 20–740 and y 20–504 of an 836 × 572 frame. The stage crops to that.
const FRAME = { x: 0, y: 0, w: 760, h: 540 };
const BASE_COUNT = 8;
const STEP_MS = 1600;
const HOLD_MS = 4600;
const RESET_MS = 900;
const LEVEL_STEP = 40;

// Each step is one small commit. Plants arrive in this order, front layers last.
const GROWTH = [
  { layer: 8, days: 2, xp: 18, msg: "docs: tidy the readme" },
  { layer: 19, days: 3, xp: 24, msg: "fix: retry on 502" },
  { layer: 9, days: 2, xp: 16, msg: "test: cover the retry" },
  { layer: 15, days: 4, xp: 32, msg: "feat: weekly journal" },
  { layer: 14, days: 3, xp: 28, msg: "refactor: split sync" },
  { layer: 18, days: 5, xp: 30, msg: "fix: timezone edge" },
  { layer: 10, days: 2, xp: 14, msg: "chore: bump deps" },
  { layer: 12, days: 6, xp: 40, msg: "feat: plant names" },
  { layer: 16, days: 4, xp: 36, msg: "test: vitality floor" },
  { layer: 13, days: 7, xp: 40, msg: "docs: privacy notes" },
  { layer: 11, days: 9, xp: 40, msg: "feat: seasons" },
  { layer: 17, days: 8, xp: 38, msg: "fix: lantern glow" },
];

// Label position and leader line, in frame units (760 × 540).
const LABELS = {
  11: { title: "Pocket maple", meta: "Grew from 11 small commits", x: 22, y: 26, line: [202, 60, 392, 126] },
  17: { title: "Autumn lantern", meta: "Seasonal · Level 4", x: 588, y: 104, line: [600, 150, 584, 262] },
};

function levelFor(xp) {
  let level = 1;
  while (xp >= (LEVEL_STEP * level * (level + 1)) / 2) level += 1;
  return level;
}

function box(layer) {
  return {
    left: `${((layer.x - FRAME.x) / FRAME.w) * 100}%`,
    top: `${((layer.y - FRAME.y) / FRAME.h) * 100}%`,
    width: `${(layer.w / FRAME.w) * 100}%`,
    height: `${(layer.h / FRAME.h) * 100}%`,
  };
}

function chipPlace(layer) {
  return {
    left: `${((layer.x + layer.w / 2 - FRAME.x) / FRAME.w) * 100}%`,
    top: `${((layer.y + layer.h * 0.38 - FRAME.y) / FRAME.h) * 100}%`,
  };
}

function totals(step) {
  const done = GROWTH.slice(0, step);
  const xp = done.reduce((sum, item) => sum + item.xp, 0);
  return {
    day: 1 + done.reduce((sum, item) => sum + item.days, 0),
    commits: step,
    xp,
    level: levelFor(xp),
  };
}

function reducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export default function HeroGarden() {
  const [step, setStep] = useState(() => (reducedMotion() ? GROWTH.length : 0));
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    if (reducedMotion()) return undefined;
    let timer;
    let current = 0;
    const tick = () => {
      if (document.hidden) {
        timer = window.setTimeout(tick, STEP_MS);
        return;
      }
      if (current < GROWTH.length) {
        current += 1;
        setStep(current);
        timer = window.setTimeout(tick, current === GROWTH.length ? HOLD_MS : STEP_MS);
        return;
      }
      setResetting(true);
      timer = window.setTimeout(() => {
        current = 0;
        setStep(0);
        setResetting(false);
        timer = window.setTimeout(tick, STEP_MS);
      }, RESET_MS);
    };
    timer = window.setTimeout(tick, 900);
    return () => window.clearTimeout(timer);
  }, []);

  const shown = new Set(GROWTH.slice(0, step).map((item) => item.layer));
  const latest = step > 0 ? GROWTH[step - 1] : null;
  const now = totals(step);
  const nextAt = (LEVEL_STEP * now.level * (now.level + 1)) / 2;
  const prevAt = (LEVEL_STEP * (now.level - 1) * now.level) / 2;
  const fill = Math.min(100, Math.round(((now.xp - prevAt) / (nextAt - prevAt)) * 100));

  return (
    <figure
      className={resetting ? "hg resetting" : "hg"}
      role="img"
      aria-label="A garden growing slowly: each small commit adds moss, ferns, flowers, a young maple and an autumn lantern."
    >
      <div className="hg-stage">
        {gardenLayers.map((layer, index) => {
          if (index < BASE_COUNT) {
            return <img key={index} className="hg-layer" src={layer.src} alt="" style={box(layer)} />;
          }
          const on = shown.has(index);
          return (
            <div key={index} className={on ? "hg-layer hg-plant on" : "hg-layer hg-plant"} style={box(layer)}>
              <img src={layer.src} alt="" className={on ? layer.motion || "" : ""} />
            </div>
          );
        })}
        <svg className="hg-lines" viewBox={`0 0 ${FRAME.w} ${FRAME.h}`} preserveAspectRatio="none" aria-hidden="true">
          {Object.entries(LABELS).map(([index, label]) => {
            const [x1, y1, x2, y2] = label.line;
            return (
              <g key={index} className={shown.has(Number(index)) ? "on" : ""}>
                <line x1={x1} y1={y1} x2={x2} y2={y2} />
                <circle cx={x2} cy={y2} r="2.5" />
              </g>
            );
          })}
        </svg>
        {Object.entries(LABELS).map(([index, label]) => (
          <p
            key={index}
            className={shown.has(Number(index)) ? "hg-label on" : "hg-label"}
            style={{ left: `${(label.x / FRAME.w) * 100}%`, top: `${(label.y / FRAME.h) * 100}%` }}
          >
            <span>{label.title}</span>
            <small>{label.meta}</small>
          </p>
        ))}
        {latest && !resetting ? (
          <p key={step} className="hg-chip" style={chipPlace(gardenLayers[latest.layer])}>
            <span>+{latest.xp} XP</span>
            <small>{latest.msg}</small>
          </p>
        ) : null}
      </div>
      <figcaption className="hg-hud">
        <span>Day {now.day}</span>
        <span>{now.commits} small commits</span>
        <span className="hg-level">Lv {now.level} · {levelName(now.level)}</span>
        <span className="hg-track" aria-hidden="true"><span style={{ width: `${fill}%` }} /></span>
      </figcaption>
    </figure>
  );
}
