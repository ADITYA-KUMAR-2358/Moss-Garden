import firstSprout from "./art/badges/first-sprout.png";
import firstSproutOff from "./art/badges/first-sprout-off.png";
import firstBloom from "./art/badges/first-bloom.png";
import firstBloomOff from "./art/badges/first-bloom-off.png";
import caretaker from "./art/badges/caretaker.png";
import caretakerOff from "./art/badges/caretaker-off.png";
import level3 from "./art/badges/level-3.png";
import level3Off from "./art/badges/level-3-off.png";
import mature from "./art/badges/mature.png";
import matureOff from "./art/badges/mature-off.png";
import sevenDays from "./art/badges/seven-days.png";
import sevenDaysOff from "./art/badges/seven-days-off.png";
import steadyWeek from "./art/badges/steady-week.png";
import steadyWeekOff from "./art/badges/steady-week-off.png";

// Wording follows the rules in backend/app/game/engine.py and backend/app/config.py.
export const BADGES = [
  { id: "first-commit", name: "First sprout", art: firstSprout, off: firstSproutOff, earned: "Your first commit took root.", hint: "Make your first counted commit." },
  { id: "steady-week", name: "Steady week", art: steadyWeek, off: steadyWeekOff, earned: "Something grew on four days in one week.", hint: "Tend the garden on four days in the same week." },
  { id: "seven-days", name: "Seven cared-for days", art: sevenDays, off: sevenDaysOff, earned: "Seven days with care, in any order.", hint: "Commit on seven different days. They don't need to be in a row." },
  { id: "caretaker", name: "Caretaker", art: caretaker, off: caretakerOff, earned: "Tended the garden with a test, a doc or a fix.", hint: "Make a commit that adds tests, docs, a fix or a cleanup." },
  { id: "mature", name: "First mature plant", art: mature, off: matureOff, earned: "A plant grew all the way to mature.", hint: "Keep tending until any plant reaches maturity." },
  { id: "bloom", name: "First bloom", art: firstBloom, off: firstBloomOff, earned: "A plant flowered for the first time.", hint: "Let any plant grow on to full bloom." },
  { id: "level-3", name: "Level 3", art: level3, off: level3Off, earned: "Reached Level 3, Damp Stone.", hint: "Reach Level 3 with lifetime XP." },
  { id: "level-5", name: "Level 5", icon: "level", earned: "Reached Level 5, Fernline.", hint: "Reach Level 5 with lifetime XP." },
  { id: "returned", name: "Came back", icon: "return", earned: "Returned after a quiet week. Nothing was lost.", hint: "Come back after seven or more quiet days." },
];

const DATE = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" });
const SHORT = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short" });

export function earnedDate(iso, short = false) {
  if (!iso) return "";
  const [year, month, day] = iso.split("-").map(Number);
  return (short ? SHORT : DATE).format(new Date(year, month - 1, day));
}

export function badgeStates(garden) {
  const earned = new Map((garden.badges || []).map((badge) => [badge.id, badge]));
  return BADGES.map((badge) => ({ ...badge, earnedOn: earned.get(badge.id)?.earned_on || null, isEarned: earned.has(badge.id) }));
}
