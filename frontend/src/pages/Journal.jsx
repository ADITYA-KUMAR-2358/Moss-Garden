import { Play, Stop } from "@phosphor-icons/react";
import { useNarration } from "../speech.js";

export default function Journal({ garden }) {
  const body = garden.journal?.body;
  const narration = useNarration({
    src: body && garden.journal.audio ? `/api/journal/${garden.journal.week_start}/audio` : null,
    text: body ? `This week in the garden. ${body}` : "",
  });
  if (!body) {
    return (
      <section className="sheet journal">
        <h1 className="journal-title">Your first entry arrives on Monday</h1>
        <p>Journals are written once a week, looking back at the week before.</p>
      </section>
    );
  }
  const source = garden.journal.source === "rules" ? "From a template" : "Written by Gemma 4, an open-weight model";
  const voiceNote = narration.voice === "elevenlabs"
    ? "Narrated by an ElevenLabs voice, only when you press Listen."
    : "Read aloud by your browser's voice, only when you press Listen.";

  return (
    <section className="sheet journal">
      <p className="overline">Field notes</p>
      <h1 className="journal-title">This week in the garden</h1>
      <p className="caption">{source}{garden.journal.source === "rules" ? ". Turn on the AI gardener in Settings for a written entry." : "."}</p>
      <p>{body}</p>
      <dl className="highlights">
        <div><dt>Active days</dt><dd>{garden.week.active_days}</dd></div>
        <div><dt>XP this week</dt><dd>{garden.week.xp}</dd></div>
        <div><dt>Plants</dt><dd>{garden.plants.length}</dd></div>
      </dl>
      {narration.supported ? (
        <div className="journal-listen">
          <button
            type="button"
            className="secondary"
            aria-pressed={narration.speaking}
            aria-busy={narration.loading}
            onClick={narration.toggle}
          >
            {narration.state === "idle"
              ? <Play size={16} weight="fill" aria-hidden="true" />
              : <Stop size={16} weight="fill" aria-hidden="true" />}
            {narration.loading ? "Preparing the voice" : narration.speaking ? "Stop" : "Listen"}
          </button>
          <p className="caption" role="status">{voiceNote} The text above is the transcript.</p>
        </div>
      ) : (
        <p className="caption">The text above is the full entry.</p>
      )}
    </section>
  );
}
