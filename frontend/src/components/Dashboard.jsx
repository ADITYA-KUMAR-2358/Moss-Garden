import { useEffect, useState } from "react";
import { ArrowRight, Leaf, Plant } from "@phosphor-icons/react";
import { Sound } from "../audio.js";
import GardenScene, { PlantMark, vitalityBand } from "./GardenScene.jsx";

const LEVEL_NAMES = [
  "",
  "Bare Soil",
  "First Sprout",
  "Damp Stone",
  "Moss Patch",
  "Fernline",
  "Leaf Litter",
  "Understory",
  "Canopy Gap",
  "Old Growth",
  "Grove Keeper",
];

const SEASONS = {
  frost: "Winter",
  rain: "Spring",
  sun: "Summer",
  leaf: "Late autumn",
};

function levelName(level) {
  return LEVEL_NAMES[level] || "Grove Keeper";
}

function localIso(date) {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

function weekCells(recent) {
  const today = new Date();
  const monday = new Date(today);
  monday.setDate(today.getDate() - ((today.getDay() + 6) % 7));
  const labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  return labels.map((label, index) => {
    const date = new Date(monday);
    date.setDate(monday.getDate() + index);
    const key = localIso(date);
    const hit = (recent || []).find((row) => row.day === key);
    return {
      label,
      key,
      commits: hit?.commits || 0,
      today: key === localIso(today),
    };
  });
}

function growthLine(row) {
  if (row.commits > 2) return "A long day of small commits.";
  if (row.commits > 0) return "Small progress still counts.";
  return "The garden kept what was already there.";
}

export default function Dashboard({ garden, onOpen, onVisit }) {
  const band = vitalityBand(garden.vitality);
  const nextName = levelName(garden.level + 1);
  const remaining = garden.next_level_xp ? Math.max(garden.next_level_xp - garden.xp, 0) : 0;
  const progress = garden.next_level_xp ? Math.min(100, Math.round((garden.xp / garden.next_level_xp) * 100)) : 100;
  const season = SEASONS[garden.season] || "This season";
  const week = weekCells(garden.recent);
  const newest = garden.plants?.[garden.plants.length - 1];
  const headline = garden.fresh
    ? "A bare patch of soil, for now."
    : band === "Resting" || garden.drought
      ? "Your garden is resting."
      : "Your garden is growing.";
  const journal = garden.journal?.body || "The garden is still here.";
  const blurb = garden.fresh
    ? "Your first seeds will appear after your next commit, review or merged pull request. There's no rush."
    : journal.split(/(?<=\.)\s/)[0];
  const growth = (garden.recent || []).slice(-3).reverse();
  const weekNumber = (() => {
    const date = new Date();
    const start = new Date(date.getFullYear(), 0, 1);
    return Math.ceil(((date - start) / 86400000 + start.getDay() + 1) / 7);
  })();

  const quiet = garden.week.active_days === 0;
  const [inspected, setInspected] = useState(null);

  useEffect(() => {
    Sound.noteXp(garden.xp);
  }, [garden.xp]);

  function inspect(day) {
    setInspected(day);
    if (!day.commits && garden.drought) Sound.play("drought");
  }

  const inspectedLine = !inspected
    ? ""
    : inspected.commits
      ? growthLine(inspected)
      : garden.drought
        ? "A dry day. The soil is resting, and nothing was lost."
        : "A quiet day. The garden kept what was already there.";

  return (
    <div className="dash">
      {garden.fresh ? (
        <section className="banner span-all" role="status">
          <h2>A bare patch of soil, for now</h2>
          <p>Your first seeds will appear after your next commit, review or merged pull request. There's no rush.</p>
        </section>
      ) : null}
      <section className="stage" aria-labelledby="garden-title">
        <div className="stage-copy">
          <p className="overline">{season} · week {weekNumber}</p>
          <h1 id="garden-title">{headline}</h1>
          <p>{blurb}</p>
        </div>
        <GardenScene
          plants={garden.plants}
          season={garden.season}
          title={`${garden.display_name} garden`}
          summaryId="garden-summary"
        />
        <p id="garden-summary" className="visually-hidden">{blurb}</p>
        <div className="stage-foot">
          <p className="caption season-note">
            <Leaf size={16} weight="fill" aria-hidden="true" />
            {season}. Lanterns may appear.
          </p>
          <div className="stage-actions">
            <button type="button" className="secondary" onClick={() => onOpen("explore")}>Explore garden</button>
            {newest ? (
              <button type="button" className="pill" onClick={() => onVisit(newest)}>
                Visit the new {newest.label || "plant"}
              </button>
            ) : null}
          </div>
        </div>
      </section>

      <aside className="ledger">
        <header className="ledger-head">
          <p>Lv {garden.level} <span>{levelName(garden.level)}</span></p>
          <p className="caption">Lifetime record</p>
        </header>
        <div className="meter">
          <div className="meter-label">
            <span>Lifetime XP</span>
            <strong>{garden.xp.toLocaleString("en")}{garden.next_level_xp ? ` / ${garden.next_level_xp.toLocaleString("en")} XP` : " XP"}</strong>
          </div>
          <div className="track" role="progressbar" aria-valuenow={garden.xp} aria-valuemax={garden.next_level_xp || garden.xp} aria-label="Lifetime XP">
            <span style={{ width: `${progress}%` }} />
          </div>
          <p className="caption">{garden.next_level_xp ? `Permanent. ${remaining.toLocaleString("en")} XP until Level ${garden.level + 1}, ${nextName}. It never goes down.` : "This is the highest level. It never goes down."}</p>
        </div>
        <div className="meter">
          <div className="meter-label">
            <span>Garden vitality</span>
            <strong>{band} · {garden.vitality}</strong>
          </div>
          <div className="track clay" aria-hidden="true"><span style={{ width: `${garden.vitality}%` }} /></div>
          <p className="caption">Temporary. Rises with activity, rests when you do.</p>
        </div>
        <section>
          <h2>Recent growth</h2>
          <ul className="growth">
            {growth.length ? growth.map((row) => (
              <li key={row.day}>
                <p>{growthLine(row)}</p>
                <p className="caption">{row.day} · {row.commits} commit{row.commits === 1 ? "" : "s"} · +{row.xp} XP</p>
              </li>
            )) : <li><p>Nothing new yet. The soil is ready.</p></li>}
          </ul>
        </section>
        {newest ? (
          <section className="discovery">
            <p className="overline">Recent discovery</p>
            <div>
              <PlantMark species={newest.species} stage={newest.stage} />
              <div>
                <h3>{newest.name}</h3>
                <p className="caption">{newest.label} · {newest.stage}. {newest.name_source === "ai" ? "Named by AI" : "Named from template"}.</p>
              </div>
            </div>
          </section>
        ) : null}
      </aside>

      <section className="week-block">
        <div className="week-head">
          <h2>This week</h2>
          <p className="caption">{garden.week.xp} XP · {garden.week.active_days} cared-for days</p>
        </div>
        <ol className="sprout-week">
          {week.map((day) => (
            <li key={day.key}>
              <button
                type="button"
                className="day-hit"
                aria-pressed={inspected?.key === day.key}
                aria-label={`${day.label}${day.today ? ", today" : ""}: ${day.commits} commit${day.commits === 1 ? "" : "s"}`}
                onClick={() => inspect(day)}
              >
                <span className={day.commits ? "mark grown" : "mark rest"} aria-hidden="true">
                  {day.commits ? <Plant size={18} weight="fill" /> : <span className="rest-dash" />}
                </span>
                <span className="count">{day.commits || ""}</span>
                <span className="caption">{day.today ? "Today" : day.label}</span>
              </button>
            </li>
          ))}
        </ol>
        {inspectedLine ? <p className="caption" role="status">{inspectedLine}</p> : null}
        <p className="caption">{quiet ? "A quiet week. The moss doesn't mind; it grows best when left alone." : "Rest days are part of the rhythm. They are marked, never counted against you."}</p>
      </section>

      <article className="journal-card">
        <p className="overline">Weekly journal</p>
        <h2>This week in the garden</h2>
        <p>{garden.journal.body}</p>
        <button type="button" className="text-link" onClick={() => onOpen("journal")}>
          Read entry <ArrowRight size={16} aria-hidden="true" />
          <span className="caption">{garden.journal.source === "rules" ? "From a template" : "Written by an open-weight model"}</span>
        </button>
      </article>
    </div>
  );
}

export { levelName, SEASONS };
