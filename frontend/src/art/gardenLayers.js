import soil from "./garden/soil.svg";
import rootsA from "./garden/roots-a.svg";
import rootsB from "./garden/roots-b.svg";
import stoneLg from "./garden/stone-lg.svg";
import stoneSm from "./garden/stone-sm.svg";
import stoneMd from "./garden/stone-md.svg";
import mossPatch from "./garden/moss-patch.svg";
import mossTuft from "./garden/moss-tuft.svg";
import leafA from "./garden/leaf-a.svg";
import leafB from "./garden/leaf-b.svg";
import treeYoung from "./garden/tree-young.svg";
import flowerYoung from "./garden/flower-young.svg";
import fernMature from "./garden/fern-mature.svg";
import mossYoung from "./garden/moss-young.svg";
import fernYoung from "./garden/fern-young.svg";
import mossMature from "./garden/moss-mature.svg";
import lanternSprout from "./garden/lantern-sprout.svg";
import sproutMature from "./garden/sprout-mature.svg";
import sprout from "./garden/sprout.svg";

export const GARDEN_W = 836;
export const GARDEN_H = 572;

export const gardenLayers = [
  { src: soil, x: 20, y: 194, w: 720, h: 310 },
  { src: rootsA, x: 202, y: 331, w: 80, h: 150 },
  { src: rootsB, x: 314, y: 336, w: 80, h: 150 },
  { src: rootsA, x: 474, y: 331, w: 80, h: 150 },
  { src: stoneLg, x: 108, y: 347, w: 56, h: 34 },
  { src: stoneSm, x: 177, y: 299, w: 22, h: 14 },
  { src: stoneMd, x: 640, y: 289, w: 40, h: 18 },
  { src: stoneLg, x: 462, y: 391, w: 56, h: 34 },
  { src: mossPatch, x: 336, y: 308, w: 128, h: 36 },
  { src: mossTuft, x: 528, y: 239, w: 64, h: 22 },
  { src: mossTuft, x: 158, y: 253, w: 64, h: 22 },
  { src: treeYoung, x: 318, y: 20, w: 204, h: 238, alt: "Young tree", motion: "sway" },
  { src: flowerYoung, x: 412, y: 44, w: 204, h: 238, alt: "Flowering plant", motion: "sway slow" },
  { src: fernMature, x: 140, y: 46, w: 204, h: 238, alt: "Mature fern", motion: "sway" },
  { src: mossYoung, x: 508, y: 62, w: 204, h: 238, alt: "Young moss", motion: "sway slow" },
  { src: fernYoung, x: 42, y: 76, w: 204, h: 238, alt: "Young fern", motion: "sway" },
  { src: mossMature, x: 252, y: 90, w: 204, h: 238, alt: "Mature moss", motion: "sway slow" },
  { src: lanternSprout, x: 466, y: 90, w: 204, h: 238, alt: "Lantern bud", motion: "glow" },
  { src: sproutMature, x: 370, y: 96, w: 204, h: 238, alt: "Sprout", motion: "sway slow" },
  { src: sprout, x: 124, y: 104, w: 204, h: 238, alt: "New sprout", motion: "sway" },
];

export const fallenLeaves = [
  { x: 305, y: 277 },
  { x: 525, y: 281 },
  { x: 633, y: 269 },
];

export const leafArt = { a: leafA, b: leafB };

export const plantArt = {
  moss: { sprout: mossYoung, young: mossYoung, mature: mossMature, bloom: mossMature },
  fern: { sprout: fernYoung, young: fernYoung, mature: fernMature, bloom: fernMature },
  maple: { sprout: treeYoung, young: treeYoung, mature: treeYoung, bloom: treeYoung },
  camellia: { sprout: flowerYoung, young: flowerYoung, mature: flowerYoung, bloom: flowerYoung },
  thyme: { sprout: flowerYoung, young: flowerYoung, mature: flowerYoung, bloom: flowerYoung },
  clover: { sprout: sprout, young: flowerYoung, mature: flowerYoung, bloom: flowerYoung },
  lantern: { sprout: lanternSprout, young: lanternSprout, mature: lanternSprout, bloom: lanternSprout },
};

export function plantSrc(species, stage) {
  const family = plantArt[species] || plantArt.moss;
  return family[stage] || family.mature || mossMature;
}
