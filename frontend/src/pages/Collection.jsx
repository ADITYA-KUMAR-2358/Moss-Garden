import { useState } from "react";
import { Sound } from "../audio.js";
import specimenFern from "../art/garden/specimen-fern.svg";
import { plantSrc } from "../art/gardenLayers.js";
import { SEASONS } from "../components/Dashboard.jsx";
import BadgeMedal from "../components/BadgeMedal.jsx";
import { badgeStates } from "../badges.js";

const TABS = ["Plants", "Badges", "Seasons"];
const SEASON_PLATES = ["Early spring", "Late spring", "Early summer", "Late summer", "Early autumn", "Late autumn", "Early winter", "Late winter"];

export default function Collection({ garden, focusPlant, onOpen }) {
  const [tab, setTab] = useState("Plants");
  const plants = garden.plants || [];
  const badges = badgeStates(garden);
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
                  <p className="specimen-found">{plant.name_source === "model" ? "Named by Gemma 4" : "Named from a template"}</p>
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
          <p className="caption medal-count">
            {badges.filter((badge) => badge.isEarned).length} of {badges.length} earned
          </p>
          <ul className="medal-grid">
            {[...badges.filter((badge) => badge.isEarned), ...badges.filter((badge) => !badge.isEarned)].map((badge) => (
              <li key={badge.id}><BadgeMedal badge={badge} /></li>
            ))}
          </ul>
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
