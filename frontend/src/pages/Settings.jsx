import { useMemo, useState } from "react";
import { Sound } from "../audio.js";
import Toggle from "../components/Toggle.jsx";

function RepoPicker({ repos, onToggleRepo, onSync }) {
  const [query, setQuery] = useState("");
  const names = repos.map((repo) => repo.full_name).join("\n");
  // Order is fixed when the list loads, so a row doesn't jump away while it's being ticked.
  const order = useMemo(() => {
    const ranked = [...repos].sort((a, b) => (
      Number(b.selected) - Number(a.selected) || a.full_name.localeCompare(b.full_name)
    ));
    return ranked.map((repo) => repo.full_name);
  }, [names]);
  const byName = new Map(repos.map((repo) => [repo.full_name, repo]));
  const needle = query.trim().toLowerCase();
  const shown = order
    .map((name) => byName.get(name))
    .filter((repo) => repo && (!needle || repo.full_name.toLowerCase().includes(needle)));
  const chosen = repos.filter((repo) => repo.selected).length;

  return (
    <div className="repo-picker">
      <div className="repo-toolbar">
        <p className="caption">
          {chosen} of {repos.length} repositories grow your garden. Only commits you authored count.
        </p>
        {repos.length > 6 ? (
          <input
            type="search"
            className="repo-search"
            placeholder="Filter repositories"
            aria-label="Filter repositories"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        ) : null}
      </div>
      <ul className="repo-list">
        {shown.map((repo) => {
          const [owner, name] = repo.full_name.split("/");
          return (
            <li key={repo.full_name}>
              <label className={repo.selected ? "repo-row on" : "repo-row"}>
                <input type="checkbox" checked={repo.selected} onChange={() => onToggleRepo(repo.full_name)} />
                <span className="repo-name">
                  <span className="repo-title">{name}</span>
                  <span className="repo-owner">{owner}</span>
                </span>
                {repo.accessible === false ? <span className="repo-tag">Can't read</span> : null}
              </label>
            </li>
          );
        })}
        {!shown.length ? <li className="caption repo-empty">No repositories match "{query}".</li> : null}
      </ul>
      <div className="repo-actions">
        <button type="button" className="primary" onClick={onSync} disabled={!chosen}>
          Read commits{chosen ? ` from ${chosen}` : ""}
        </button>
      </div>
    </div>
  );
}

function unlockedSounds(garden) {
  const spring = garden.audio?.spring_level;
  const rain = garden.audio?.rain_level;
  const rows = [
    ["Leaf brush", (garden.plants || []).length > 0],
    ["Sprout", (garden.plants || []).length > 0],
    ["Level chime", garden.level >= 2],
    ["Badge bell", (garden.badges || []).length > 0],
    ["Pebble drop", garden.xp > 0],
    ["Dry wind", Boolean(garden.drought)],
    ["Comeback", (garden.badges || []).some((badge) => badge.id === "returned")],
    ["Saved card", localStorage.getItem("moss-card-saved") === "yes"],
    ["Spring bed", spring != null && garden.level >= spring],
    ["Autumn bed", garden.season === "leaf"],
    ["Winter bed", garden.season === "frost"],
    ["Rain", rain != null && garden.level >= rain],
    ["Garden music", true],
  ];
  return {
    open: rows.filter(([, on]) => on).map(([name]) => name),
    quiet: rows.filter(([, on]) => !on).map(([name]) => name),
  };
}

export default function Settings({
  garden, themeChoice, onTheme, soundOn, onSound,
  repos, onGitHub, onToggleRepo, onSync, onShare, onDescribe, described, summary,
  status, onLogout, onDeleted, onAi, aiBusy,
}) {
  const ai = garden.ai || {};
  const aiLocked = !ai.can_change || !ai.available;
  const aiNote = !ai.can_change
    ? "The shared demo garden keeps this off. Sign in with GitHub to use it on your own garden."
    : !ai.available
      ? "This server has no model set up, so plants keep template names and the journal stays a plain summary."
      : ai.enabled
        ? "On. New plants are named and this week's journal is written by the model. Only counts and plant species are sent."
        : "Off. Turning it on renames up to three plants now and rewrites this week's journal.";
  const sounds = unlockedSounds(garden);
  const [volumes, setVolumes] = useState(() => Sound.volumes());
  const [confirming, setConfirming] = useState(false);
  const [typed, setTyped] = useState("");
  const [error, setError] = useState("");

  async function removeGarden() {
    if (typed !== garden.login) {
      setError("Type your GitHub login to confirm.");
      return;
    }
    const response = await fetch("/api/account", { method: "DELETE" });
    if (!response.ok) {
      setError("The garden could not be deleted. Try again.");
      return;
    }
    onDeleted();
  }

  return (
    <section className="sheet settings">
      <p className="overline">Account</p>
      <h1 className="sheet-title">Settings</h1>
      <p>Signed in as <span className="mono">@{garden.login}</span>.</p>

      <h2>Appearance</h2>
      <div className="segmented" role="radiogroup" aria-label="Theme">
        {["light", "dark", "system"].map((choice) => (
          <button key={choice} type="button" role="radio" aria-checked={themeChoice === choice} onClick={() => onTheme(choice)}>
            {choice[0].toUpperCase() + choice.slice(1)}
          </button>
        ))}
      </div>

      <h2>AI gardener</h2>
      <div className="setting-row">
        <span>
          Plant names and weekly journal
          <span className="caption setting-sub">{ai.model || "Gemma 4"}</span>
        </span>
        <Toggle
          checked={Boolean(ai.enabled)}
          disabled={aiLocked || aiBusy}
          busy={aiBusy}
          label="AI gardener"
          onClick={() => onAi(!ai.enabled)}
        />
      </div>
      <p className="caption">{aiNote} Your code and repository names are never sent.</p>

      <h2>Sound</h2>
      <div className="setting-row">
        <span>Garden sound</span>
        <button type="button" className="sound-toggle" aria-pressed={soundOn} onClick={onSound}>
          {soundOn ? "Sound on" : "Sound off"}
        </button>
      </div>
      <p className="caption">
        Sound stays quiet until you turn it on. Every sound has something on screen as well.
        {Sound.motionReduced() ? " Season beds stay off while reduced motion is on. Music still follows these sliders." : ""}
      </p>
      {[
        ["master", "Master"],
        ["music", "Background music"],
        ["effects", "Effects"],
        ["ambient", "Garden ambience"],
      ].map(([bus, label]) => (
        <label className="volume-row" key={bus} htmlFor={`vol-${bus}`}>
          <span>{label}</span>
          <input
            id={`vol-${bus}`}
            type="range"
            min="0"
            max="100"
            value={Math.round((volumes[bus] || 0) * 100)}
            aria-valuetext={`${Math.round((volumes[bus] || 0) * 100)} percent`}
            onChange={(event) => setVolumes(Sound.setVolume(bus, Number(event.target.value) / 100))}
          />
          <span className="caption">{Math.round((volumes[bus] || 0) * 100)}</span>
        </label>
      ))}
      <h2>Sounds you've unlocked</h2>
      {sounds.open.length ? (
        <ul className="sound-list">
          {sounds.open.map((name) => <li key={name}>{name}</li>)}
        </ul>
      ) : <p className="caption">None yet. The garden is quiet, and that is fine.</p>}
      {sounds.quiet.length ? <p className="caption">Still quiet: {sounds.quiet.join(", ")}.</p> : null}

      <h2>Data sources</h2>
      {garden.demo ? (
        <>
          <p className="caption">This is the demo garden. Connect GitHub to grow one from your own public commits.</p>
          <button type="button" className="primary" onClick={onGitHub}>Connect GitHub</button>
        </>
      ) : repos.length ? (
        <RepoPicker repos={repos} onToggleRepo={onToggleRepo} onSync={onSync} />
      ) : <p className="caption">No repositories are connected yet.</p>}

      <h2>Sharing</h2>
      <div className="actions">
        <button type="button" className="secondary" onClick={onShare}>Share card</button>
        <button type="button" className="secondary" aria-pressed={described} onClick={onDescribe}>Describe my garden</button>
      </div>
      {described ? <p className="summary">{summary}</p> : null}

      <h2>Data</h2>
      <div className="actions">
        <a className="secondary" href="/api/export" download>Export my garden</a>
        <button type="button" className="secondary" onClick={onLogout}>Log out</button>
        {garden.demo ? null : (
          <button type="button" className="danger-button" onClick={() => setConfirming(true)}>Delete my garden</button>
        )}
      </div>
      {garden.demo ? <p className="caption">The demo garden is shared, so it can't be deleted.</p> : null}
      <p className="note" role="status">{status}</p>

      {confirming ? (
        <div className="dialog-back" role="presentation" onClick={() => setConfirming(false)}>
          <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="delete-title" onClick={(event) => event.stopPropagation()}>
            <h2 id="delete-title">Delete your garden?</h2>
            <p>This removes all plants, journals and XP from Moss Garden. Your GitHub account isn't affected.</p>
            <label>
              Type {garden.login} to confirm
              <input value={typed} onChange={(event) => setTyped(event.target.value)} aria-invalid={Boolean(error)} />
            </label>
            {error ? <p className="danger" role="alert">{error}</p> : null}
            <div className="actions">
              <button type="button" className="danger-button" onClick={removeGarden}>Delete garden</button>
              <button type="button" className="secondary" onClick={() => setConfirming(false)}>Keep my garden</button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
