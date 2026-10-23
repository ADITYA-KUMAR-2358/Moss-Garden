import { useState } from "react";
import { Sound } from "../audio.js";
import { MagnifyingGlassMinus, MagnifyingGlassPlus, ArrowCounterClockwise } from "@phosphor-icons/react";
import GardenScene, { PlantMark } from "../components/GardenScene.jsx";

export default function Explore({ garden, onOpen }) {
  const [zoom, setZoom] = useState(1);
  const [labels, setLabels] = useState(true);
  const [selected, setSelected] = useState(garden.plants[0] || null);
  const plants = garden.plants || [];

  return (
    <section className="explore">
      <div className="explore-bar">
        <h1 className="sheet-title">Garden</h1>
        <div className="actions">
          <button type="button" className="secondary" aria-pressed={labels} onClick={() => setLabels((value) => !value)}>
            {labels ? "Hide labels" : "Show labels"}
          </button>
          <button type="button" className="secondary" onClick={() => setZoom((value) => Math.min(2.5, Math.round((value + 0.25) * 100) / 100))} aria-label="Zoom in">
            <MagnifyingGlassPlus size={18} aria-hidden="true" />
          </button>
          <button type="button" className="secondary" onClick={() => setZoom((value) => Math.max(1, Math.round((value - 0.25) * 100) / 100))} aria-label="Zoom out">
            <MagnifyingGlassMinus size={18} aria-hidden="true" />
          </button>
          <button type="button" className="secondary" onClick={() => setZoom(1)} aria-label="Reset view">
            <ArrowCounterClockwise size={18} aria-hidden="true" />
          </button>
        </div>
      </div>
      <div className="explore-layout">
        <div className="explore-canvas" style={{ "--zoom": zoom }}>
          <div className="explore-scale">
            <GardenScene plants={plants} season={garden.season} title={`${garden.display_name} garden`} summaryId="explore-summary" />
            {labels && selected ? <p className="explore-label">{selected.name}</p> : null}
          </div>
        </div>
        <aside className="inspector" aria-live="polite">
          {selected ? (
            <>
              <PlantMark species={selected.species} stage={selected.stage} size={120} />
              <h2 className="plant-name">{selected.name}</h2>
              <p className="caption">{selected.label} · {selected.stage}</p>
              <p>{selected.description || "Grew from commits kept in this garden."}</p>
              <p className="caption">{selected.name_source === "model" ? "Named by Gemma 4" : "Named from template"}</p>
              <button type="button" className="text-link" onClick={() => onOpen("collection")}>View in collection</button>
            </>
          ) : (
            <>
              <h2>A bare patch of soil, for now</h2>
              <p>Your first seeds will appear after your next commit, review or merged pull request. There's no rush.</p>
            </>
          )}
          <ul className="plant-picks">
            {plants.map((plant) => (
              <li key={plant.slot}>
                <button
                  type="button"
                  aria-pressed={selected?.slot === plant.slot}
                  onClick={() => setSelected(plant)}
                  onMouseEnter={() => Sound.play("plant-brush")}
                  onFocus={() => Sound.play("plant-brush")}
                >
                  <PlantMark species={plant.species} stage={plant.stage} size={36} />
                  {plant.name}
                </button>
              </li>
            ))}
          </ul>
        </aside>
      </div>
      <p id="explore-summary" className="visually-hidden">{plants.map((plant) => plant.name).join(", ") || "No plants yet."}</p>
    </section>
  );
}
