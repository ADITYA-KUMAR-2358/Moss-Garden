import { Sound } from "../audio.js";

export default function Journal({ garden }) {
  const body = garden.journal?.body;
  if (!body) {
    return (
      <section className="sheet journal">
        <h1 className="journal-title">Your first entry arrives on Monday</h1>
        <p>Journals are written once a week, looking back at the week before.</p>
      </section>
    );
  }
  const source = garden.journal.source === "rules" ? "From a template" : "Written by an open-weight model";

  async function listen() {
    const response = await fetch(`/api/journal/${garden.journal.week_start}/audio`);
    if (!response.ok) return;
    Sound.playBlob(await response.blob());
  }

  return (
    <section className="sheet journal">
      <p className="overline">Field notes</p>
      <h1 className="journal-title">This week in the garden</h1>
      <p className="caption">{source}{garden.journal.source === "rules" ? ". AI journal is off." : ""}</p>
      <p>{body}</p>
      <dl className="highlights">
        <div><dt>Active days</dt><dd>{garden.week.active_days}</dd></div>
        <div><dt>XP this week</dt><dd>{garden.week.xp}</dd></div>
        <div><dt>Plants</dt><dd>{garden.plants.length}</dd></div>
      </dl>
      <p className="caption">The text above is the transcript.</p>
      {garden.journal.audio ? (
        <button type="button" className="secondary" onClick={listen}>Listen</button>
      ) : null}
    </section>
  );
}
