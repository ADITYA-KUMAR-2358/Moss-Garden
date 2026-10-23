import { useState } from "react";
import { Sound } from "../audio.js";

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
  status, onLogout, onDeleted,
}) {
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
        <div className="repo-list">
          {repos.map((repo) => (
            <label key={repo.full_name} className="mono">
              <input type="checkbox" checked={repo.selected} onChange={() => onToggleRepo(repo.full_name)} />
              {repo.full_name}
            </label>
          ))}
          <button type="button" className="primary" onClick={onSync}>Read commits</button>
        </div>
      ) : <p className="caption">No repositories are connected yet.</p>}

      <h2>Sharing</h2>
      <div className="actions">
        <button type="button" className="secondary" onClick={onShare}>Share card</button>
        <button type="button" className="secondary" aria-pressed={described} onClick={onDescribe}>Describe my garden</button>
      </div>
      {described ? <p className="summary">{summary}</p> : null}

      <h2>Data</h2>
      <div className="actions">
        <button type="button" className="secondary" onClick={onLogout}>Log out</button>
        <button type="button" className="danger-button" onClick={() => setConfirming(true)}>Delete my garden</button>
      </div>
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
