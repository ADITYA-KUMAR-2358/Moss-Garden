import { useEffect } from "react";
import { Sound } from "../audio.js";
import { levelName } from "../components/Dashboard.jsx";

export default function LevelUp({ garden, onClose, onShare }) {
  const name = levelName(garden.level);
  useEffect(() => {
    Sound.playOnce("sprout", `sprout-${garden.level}`);
    Sound.playOnce("level-up", `level-${garden.level}`);
  }, []);
  return (
    <div className="dialog-back" role="presentation">
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="level-title">
        <p className="overline">Level {garden.level}</p>
        <h2 id="level-title" className="journal-title" tabIndex={-1}>{name}</h2>
        <p>Light reaches a little further now. Your garden kept every plant, and the next places to grow are open.</p>
        <div className="actions">
          <button type="button" className="primary" onClick={onClose}>See my garden</button>
          <button type="button" className="secondary" onClick={onClose}>Close</button>
        </div>
        <button type="button" className="text-link" onClick={onShare}>Make a share card</button>
      </div>
    </div>
  );
}
