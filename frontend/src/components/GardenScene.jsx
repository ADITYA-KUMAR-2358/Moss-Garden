import { gardenLayers, plantSrc } from "../art/gardenLayers.js";

export function vitalityBand(score) {
  if (score >= 80) return "Lush";
  if (score >= 55) return "Settled";
  if (score >= 30) return "Quiet";
  return "Resting";
}

export function gardenSummary(garden) {
  const names = (garden.plants || []).map((plant) => plant.name).join(", ");
  const band = vitalityBand(garden.vitality).toLowerCase();
  if (!garden.plants?.length) {
    return "A bare patch of soil, for now. Nothing has been planted yet.";
  }
  return `${garden.display_name || "This"} garden in ${garden.season}. ${garden.plants.length} plants: ${names}. The garden feels ${band}.`;
}

export function PlantMark({ species, stage, size = 72 }) {
  return (
    <img
      className="plant-mark"
      src={plantSrc(species, stage)}
      width={size}
      height={size}
      alt=""
    />
  );
}

export default function GardenScene({ plants = [], title, summaryId }) {
  const soil = gardenLayers[0];
  const plantLayers = gardenLayers.slice(11);
  return (
    <div
      className="garden-sheet"
      role="img"
      aria-label={title || "A floating garden of moss, ferns and a young tree"}
      aria-describedby={summaryId || undefined}
    >
      <div className="garden-board">
        <img
          className="garden-layer"
          src={soil.src}
          alt=""
          width={soil.w}
          height={soil.h}
          style={{ left: soil.x, top: soil.y, width: soil.w, height: soil.h }}
        />
        {plants.map((plant, index) => {
          const layer = plantLayers[index % plantLayers.length];
          return (
            <img
              key={plant.slot}
              className="garden-layer"
              src={plantSrc(plant.species, plant.stage)}
              alt=""
              width={layer.w}
              height={layer.h}
              style={{ left: layer.x, top: layer.y, width: layer.w, height: layer.h }}
            />
          );
        })}
      </div>
    </div>
  );
}
