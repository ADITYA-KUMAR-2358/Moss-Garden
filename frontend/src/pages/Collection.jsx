import { useState } from "react";
import { Sound } from "../audio.js";
import specimenFern from "../art/garden/specimen-fern.svg";
import { plantSrc } from "../art/gardenLayers.js";
import { SEASONS } from "../components/Dashboard.jsx";
import firstSprout from "../art/badges/first-sprout.png";
import firstSproutOff from "../art/badges/first-sprout-off.png";
import firstBloom from "../art/badges/first-bloom.png";
import firstBloomOff from "../art/badges/first-bloom-off.png";
import caretaker from "../art/badges/caretaker.png";
import caretakerOff from "../art/badges/caretaker-off.png";
import level3 from "../art/badges/level-3.png";
import level3Off from "../art/badges/level-3-off.png";
import mature from "../art/badges/mature.png";
import matureOff from "../art/badges/mature-off.png";
import sevenDays from "../art/badges/seven-days.png";
import sevenDaysOff from "../art/badges/seven-days-off.png";
import steadyWeek from "../art/badges/steady-week.png";
import steadyWeekOff from "../art/badges/steady-week-off.png";

const TABS = ["Plants", "Badges", "Seasons"];
const SEASON_PLATES = ["Early spring", "Late spring", "Early summer", "Late summer", "Early autumn", "Late autumn", "Early winter", "Late winter"];

const BADGE_ART = [
  ["first-commit", firstSprout, firstSproutOff, "First sprout"],
  ["bloom", firstBloom, firstBloomOff, "First bloom"],
  ["caretaker", caretaker, caretakerOff, "Caretaker"],
  ["level-3", level3, level3Off, "Level 3"],
  ["mature", mature, matureOff, "First mature plant"],
  ["seven-days", sevenDays, sevenDaysOff, "Seven cared-for days"],
  ["steady-week", steadyWeek, steadyWeekOff, "Steady week"],
];

export default function Collection({ garden, focusPlant, onOpen }) {
  const [tab, setTab] = useState("Plants");
  const plants = garden.plants || [];
  const current = SEASONS[garden.season] || "Late autumn";

  return (
    <section className="sheet">
      <p className="overline">Specimen plates</p>
      <h1 className="sheet-title">Collection</h1>
      <p className="caption">{plants.length} plants · {garden.badges.length} badges</p>
      <div className="tabs" role="tablist" aria-label="Collection">
        {TABS.map((item) => (
          <button key={item} type="button" role="tab" aria-selected={tab === item} onClick={() => setTab(item)}>{item}</button>
        ))}
      </div>

      {tab === "Plants" ? (
        plants.length ? (
          <ul className="specimens">
            {plants.map((plant) => (
              <li
                className={focusPlant?.slot === plant.slot ? "specimen current" : "specimen"}
                key={plant.slot}
                tabIndex={0}
                aria-label={plant.name}
                onMouseEnter={() => Sound.play("plant-brush")}
                onFocus={() => Sound.play("plant-brush")}
              >
                <div className="specimen-art">
                  <img src={plant.species === "fern" ? specimenFern : plantSrc(plant.species, plant.stage)} alt="" />
                </div>
                <div className="specimen-copy">
                  <h2 className="plant-name">{plant.name}</h2>
                  <p className="specimen-meta">{plant.label} · {plant.stage}</p>
                  <p className="specimen-found">{plant.name_source === "ai" ? "Named by an open-weight model" : "Named from a template"}</p>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <div className="empty">
            <h2>Nothing pressed in the book yet</h2>
            <p>Plants you discover will be kept here, one page each.</p>
            <button type="button" className="secondary" onClick={() => onOpen("garden")}>Back to garden</button>
          </div>
        )
      ) : null}

      {tab === "Badges" ? (
        <>
          <ul className="badge-grid">
            {BADGE_ART.map(([id, earnedArt, lockedArt, name]) => {
              const earned = garden.badges.some((badge) => badge.id === id);
              return (
                <li key={id}>
                  <img src={earned ? earnedArt : lockedArt} alt={earned ? `${name}, earned` : `${name}, not yet earned`} />
                </li>
              );
            })}
          </ul>
          {garden.badges.some((badge) => !BADGE_ART.some(([id]) => id === badge.id)) ? (
            <ul className="badges">
              {garden.badges.filter((badge) => !BADGE_ART.some(([id]) => id === badge.id)).map((badge) => (
                <li key={badge.id}>{badge.label}</li>
              ))}
            </ul>
          ) : null}
          <p className="caption">More badges appear as your garden grows.</p>
        </>
      ) : null}

      {tab === "Seasons" ? (
        <ul className="specimens">
          {SEASON_PLATES.map((name) => (
            <li className="plate" key={name}>
              <h2 className="plant-name">{name}</h2>
              <p>{name === current && plants[0] ? `${plants[0].name}, found this season.` : `Visit in ${name} to see what grows.`}</p>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
