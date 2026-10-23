import { useState } from "react";
import { Plant } from "@phosphor-icons/react";
import { Sound } from "../audio.js";
import GardenScene from "../components/GardenScene.jsx";
import { SEASONS, levelName } from "../components/Dashboard.jsx";

function wrap(ctx, text, x, y, max, lineHeight) {
  const words = text.split(" ");
  let line = "";
  let cursor = y;
  words.forEach((word) => {
    const next = line ? `${line} ${word}` : word;
    if (ctx.measureText(next).width > max) {
      ctx.fillText(line, x, cursor);
      line = word;
      cursor += lineHeight;
    } else {
      line = next;
    }
  });
  if (line) ctx.fillText(line, x, cursor);
}

export default function Share({ garden }) {
  const season = SEASONS[garden.season] || "This season";
  const line = `${season}. ${garden.plants.length} plant${garden.plants.length === 1 ? "" : "s"} in the garden.`;
  const [copied, setCopied] = useState(false);

  function download() {
    const canvas = document.createElement("canvas");
    canvas.width = 1200;
    canvas.height = 630;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#EFE6D4";
    ctx.fillRect(0, 0, 1200, 630);
    ctx.fillStyle = "#F4F0E5";
    ctx.fillRect(0, 0, 540, 630);
    ctx.fillStyle = "#202B24";
    ctx.font = "600 20px Fraunces Variable, Georgia, serif";
    ctx.fillText("Moss Garden", 64, 88);
    ctx.fillStyle = "#5E6057";
    ctx.font = "15px Inter Variable, sans-serif";
    ctx.fillText(`@${garden.login}'s garden`, 64, 250);
    ctx.fillStyle = "#202B24";
    ctx.font = "400 36px Fraunces Variable, Georgia, serif";
    ctx.fillText(`Level ${garden.level} · ${levelName(garden.level)}`, 64, 300);
    ctx.fillStyle = "#34483A";
    ctx.font = "17px Inter Variable, sans-serif";
    wrap(ctx, line, 64, 340, 420, 26);
    ctx.strokeStyle = "#D6CDBB";
    ctx.beginPath();
    ctx.moveTo(64, 500);
    ctx.lineTo(480, 500);
    ctx.stroke();
    ctx.fillStyle = "#5E6057";
    ctx.font = "15px Inter Variable, sans-serif";
    ctx.fillText(`${garden.xp.toLocaleString("en")} lifetime XP`, 64, 532);
    ctx.font = "italic 18px Fraunces Variable, Georgia, serif";
    ctx.fillStyle = "#34483A";
    ctx.fillText("Small commits. Slow growth. A garden that remembers.", 64, 562);
    const picture = document.querySelector(".share-card .garden-sheet img");
    if (picture) ctx.drawImage(picture, 560, 90, 580, 460);
    Sound.play("card-saved");
    localStorage.setItem("moss-card-saved", "yes");
    const link = document.createElement("a");
    link.href = canvas.toDataURL("image/png");
    link.download = "moss-garden.png";
    link.click();
  }

  return (
    <section className="sheet">
      <p className="overline">Export</p>
      <h1 className="sheet-title">Share card</h1>
      <article className="share-card">
        <div className="share-copy">
          <p className="wordmark"><Plant size={18} weight="regular" aria-hidden="true" /> Moss Garden</p>
          <p className="caption">@{garden.login}'s garden</p>
          <p className="share-level">Level {garden.level} · {levelName(garden.level)}</p>
          <p>{line}</p>
          <p className="share-rule">{garden.xp.toLocaleString("en")} lifetime XP</p>
          <p className="tagline">Small commits. Slow growth. A garden that remembers.</p>
        </div>
        <div className="share-garden">
          <GardenScene title={`${garden.display_name} garden`} />
        </div>
      </article>
      <p id="share-summary" className="visually-hidden">{garden.share.text}</p>
      <div className="actions">
        <button type="button" className="primary" onClick={download}>Download image</button>
        <button
          type="button"
          className="secondary"
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(garden.share.text);
              setCopied(true);
            } catch {
              setCopied(false);
            }
          }}
        >
          {copied ? "Copied" : "Copy text"}
        </button>
      </div>
    </section>
  );
}
