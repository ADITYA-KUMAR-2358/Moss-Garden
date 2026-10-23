import gardenSheet from "../art/garden-sheet.svg";
import { plantSrc } from "../art/gardenLayers.js";

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

export default function GardenScene({ title, summaryId }) {
  return (
    <div
      className="garden-sheet"
      role="img"
      aria-label={title || "A floating garden of moss, ferns and a young tree"}
      aria-describedby={summaryId || undefined}
    >
      <img src={gardenSheet} alt="" />
    </div>
  );
}
