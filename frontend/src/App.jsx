import { useEffect, useRef, useState } from "react";
import { BookOpen, Gear, Plant, SpeakerHigh, SpeakerSlash, SquaresFour } from "@phosphor-icons/react";
import { Sound } from "./audio.js";
import Dashboard, { levelName } from "./components/Dashboard.jsx";
import { gardenSummary, vitalityBand } from "./components/GardenScene.jsx";
import Marketing from "./components/Marketing.jsx";
import SiteFooter from "./components/SiteFooter.jsx";
import Collection from "./pages/Collection.jsx";
import Connect from "./pages/Connect.jsx";
import Explore from "./pages/Explore.jsx";
import Journal from "./pages/Journal.jsx";
import LevelUp from "./pages/LevelUp.jsx";
import Settings from "./pages/Settings.jsx";
import Share from "./pages/Share.jsx";
import Toasts from "./components/Toasts.jsx";
import offTrack from "./art/toggle/off.svg";
import onTrack from "./art/toggle/on.svg";

const NAV = [
  ["garden", "Garden"],
  ["collection", "Collection"],
  ["journal", "Journal"],
  ["settings", "Settings"],
];

export default function App() {
  const [garden, setGarden] = useState(null);
  const [repos, setRepos] = useState([]);
  const [note, setNote] = useState("");
  const [status, setStatus] = useState("");
  const [soundOn, setSoundOn] = useState(false);
  const [githubReady, setGithubReady] = useState(false);
  const [githubSetup, setGithubSetup] = useState(false);
  const [themeChoice, setThemeChoice] = useState(localStorage.getItem("moss-theme") || "system");
  const [view, setView] = useState("garden");
  const [gate, setGate] = useState("home");
  const [atHome, setAtHome] = useState(() => window.location.hash !== "#garden");
  const [connectPhase, setConnectPhase] = useState("ready");
  const [described, setDescribed] = useState(false);
  const [focusPlant, setFocusPlant] = useState(null);
  const [levelUp, setLevelUp] = useState(false);
  const [offline, setOffline] = useState(!navigator.onLine);
  const [toasts, setToasts] = useState([]);
  const toastSeq = useRef(0);

  function dismissToast(id) {
    setToasts((list) => list.filter((item) => item.id !== id));
  }

  function pushToast(toast) {
    const id = toastSeq.current + 1;
    toastSeq.current = id;
    setToasts((list) => [...list.slice(-3), { id, ...toast }]);
    window.setTimeout(() => dismissToast(id), 8000);
  }

  function flipTheme() {
    onTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
  }

  const darkTheme = themeChoice === "dark" || (
    themeChoice === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches
  );

  async function loadGarden() {
    let response;
    try {
      response = await fetch("/api/garden");
    } catch {
      setNote("The garden could not be loaded.");
      return;
    }
    if (response.status === 401) {
      setGarden(null);
      return;
    }
    if (!response.ok) {
      setNote("The garden could not be loaded.");
      return;
    }
    const next = await response.json();
    const previous = JSON.parse(localStorage.getItem("moss-snapshot") || "null");
    if (previous) {
      const known = new Set((previous.plants || []).map((plant) => plant.slot));
      const arrived = (next.plants || []).filter((plant) => !known.has(plant.slot));
      if (arrived.length) {
        const plant = arrived[0];
        pushToast({
          tone: "plant",
          message: plant.species === "fern"
            ? "A new fern found its place."
            : `A new ${String(plant.label || plant.species).toLowerCase()} found its place.`,
          actionLabel: "View",
          action: () => {
            setFocusPlant(plant);
            setView("collection");
            setAtHome(false);
            if (window.location.hash !== "#garden") history.pushState(null, "", "#garden");
          },
        });
      }
    }
    localStorage.setItem("moss-snapshot", JSON.stringify(next));
    if (previous && (next.badges || []).length > (previous.badges || []).length) {
      Sound.play("badge");
      pushToast({
        tone: "ok",
        message: "A new badge is in the collection.",
        actionLabel: "View",
        action: () => setView("collection"),
      });
    }
    const cameBack = Sound.noteVisit(next.return_gap_days);
    const seen = Number(localStorage.getItem("moss-celebrated-level") || 0);
    if (previous && next.level > previous.level && next.level > seen) setLevelUp(true);
    setGarden(next);
    const band = vitalityBand(next.vitality);
    setStatus(cameBack
      ? "Welcome back. The garden kept every plant."
      : band === "Resting" || next.drought
        ? "Your garden is resting. It's all still here."
        : next.fresh
          ? "A bare patch of soil, for now."
          : "");
    if (cameBack) Sound.play("comeback");
    if (!next.demo) {
      const repoResponse = await fetch("/api/repos");
      if (repoResponse.ok) setRepos((await repoResponse.json()).repos);
    } else {
      setRepos([]);
    }
  }

  useEffect(() => {
    if (themeChoice !== "system") return undefined;
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => onTheme("system");
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, [themeChoice]);

  useEffect(() => {
    setSoundOn(Sound.restoreAudioPreference());
    Sound.armGesture();
    fetch("/api/auth/status")
      .then((response) => response.json())
      .then((payload) => {
        setGithubReady(Boolean(payload.github));
        setGithubSetup(Boolean(payload.setup));
      })
      .catch(() => setGithubReady(false));
    const query = new URLSearchParams(window.location.search);
    if (query.get("github") === "off") {
      history.replaceState(null, "", window.location.pathname);
      setGate("connect");
    }
    loadGarden();
    const syncHash = () => setAtHome(window.location.hash !== "#garden");
    window.addEventListener("hashchange", syncHash);
    const online = () => setOffline(false);
    const off = () => setOffline(true);
    window.addEventListener("online", online);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("hashchange", syncHash);
      window.removeEventListener("online", online);
      window.removeEventListener("offline", off);
    };
  }, []);

  function onTheme(choice) {
    const resolved = choice === "system"
      ? (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
      : choice;
    document.documentElement.dataset.theme = resolved;
    if (choice === "system") localStorage.removeItem("moss-theme");
    else localStorage.setItem("moss-theme", choice);
    setThemeChoice(choice);
  }

  function showHome(event) {
    event?.preventDefault();
    setAtHome(true);
    setGate("home");
    if (window.location.hash) history.pushState(null, "", window.location.pathname + window.location.search);
    window.scrollTo(0, 0);
  }

  function showApp() {
    setAtHome(false);
    setGate("home");
    setView("garden");
    if (window.location.hash !== "#garden") history.pushState(null, "", "#garden");
    window.scrollTo(0, 0);
  }

  function openConnect(event) {
    event?.preventDefault();
    setAtHome(true);
    setGate("connect");
    setConnectPhase("ready");
    if (window.location.hash) history.pushState(null, "", window.location.pathname + window.location.search);
    window.scrollTo(0, 0);
  }

  function continueGitHub() {
    if (githubReady) window.location.href = "/auth/github";
    else if (githubSetup) window.location.href = "/auth/github/setup";
  }

  async function enterDemo() {
    setNote("Opening the demo garden.");
    const response = await fetch("/api/demo/enter", { method: "POST" });
    if (!response.ok) {
      pushToast({
        tone: "warn",
        message: "The demo garden could not be opened.",
        actionLabel: "Try again",
        action: () => enterDemo(),
      });
      setNote("");
      return;
    }
    setNote("");
    await loadGarden();
    showApp();
  }

  function onSound() {
    const next = !soundOn;
    Sound.setEnabled(next);
    setSoundOn(next);
  }

  useEffect(() => {
    if (!garden) return;
    Sound.setScene({
      level: garden.level,
      springLevel: garden.audio?.spring_level,
      rainLevel: garden.audio?.rain_level,
    });
    Sound.setAmbient(garden.season);
  }, [garden, soundOn]);

  function onToggleRepo(fullName) {
    setRepos((current) => current.map((item) => (
      item.full_name === fullName ? { ...item, selected: !item.selected } : item
    )));
  }

  async function syncRepos() {
    const names = repos.filter((repo) => repo.selected).map((repo) => repo.full_name);
    let saved;
    try {
      saved = await fetch("/api/repos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ full_names: names }),
      });
    } catch {
      saved = { ok: false };
    }
    if (!saved.ok) {
      pushToast({
        tone: "warn",
        message: "Sync paused. GitHub didn\u2019t respond.",
        actionLabel: "Try again",
        action: () => syncRepos(),
      });
      return;
    }
    let response;
    try {
      response = await fetch("/api/sync", { method: "POST" });
    } catch {
      response = { ok: false };
    }
    if (!response.ok) {
      pushToast({
        tone: "warn",
        message: "Sync paused. GitHub didn\u2019t respond.",
        actionLabel: "Try again",
        action: () => syncRepos(),
      });
      return;
    }
    const payload = await response.json();
    await loadGarden();
    if (payload.status !== "demo") {
      pushToast({
        tone: "ok",
        message: `GitHub connected. ${payload.imported ?? 0} commits found.`,
        actionLabel: "Open garden",
        action: () => setView("garden"),
      });
    }
  }

  async function logout() {
    try {
      await fetch("/api/logout", { method: "POST" });
    } catch {
      pushToast({ tone: "warn", message: "Log out did not reach the server. The garden is closed on this screen." });
    }
    pushToast({ tone: "info", message: "Your garden will be here when you return." });
    setGarden(null);
    setRepos([]);
    setView("garden");
    setGate("home");
    setAtHome(true);
    if (window.location.hash) history.pushState(null, "", window.location.pathname + window.location.search);
  }

  function dismissLevelUp() {
    if (garden) localStorage.setItem("moss-celebrated-level", String(garden.level));
    setLevelUp(false);
    setView("garden");
  }

  const gardenCurrent = view === "garden" || view === "explore";

  return (
    <>
      <a className="skip" href="#content">Skip to content</a>
      <header className={garden && !atHome ? "app-header" : "nav"}>
        <div className="brand-lockup">
          <a className="wordmark" href="/" onClick={showHome}>
            <Plant size={18} weight="fill" aria-hidden="true" />
            Moss Garden
          </a>
          {garden && !atHome ? (
            <span className="level-chip">
              <span>Lv {garden.level}</span>
              <span>{levelName(garden.level)}</span>
            </span>
          ) : null}
        </div>
        {garden && !atHome ? (
          <nav className="app-nav" aria-label="Main">
            {NAV.map(([id, label]) => (
              <button key={id} type="button" aria-current={(id === "garden" ? gardenCurrent : view === id) ? "page" : undefined} onClick={() => setView(id)}>
                {label}
              </button>
            ))}
          </nav>
        ) : (
          <nav className="nav-links" aria-label="Main">
            <a href="#how">How it grows</a>
            <a href="#journal">Journal</a>
            <a href="#privacy">Privacy</a>
            <a href="#faq">FAQ</a>
          </nav>
        )}
        <div className="actions">
          {atHome || !garden ? (
            <button
              type="button"
              className="theme-switch"
              aria-pressed={darkTheme}
              aria-label={darkTheme ? "Switch to light theme" : "Switch to dark theme"}
              onClick={flipTheme}
            >
              <img src={darkTheme ? onTrack : offTrack} alt="" width="36" height="20" />
              <span>{darkTheme ? "Dark" : "Light"}</span>
            </button>
          ) : null}
          {garden && !atHome ? (
            <button type="button" className="sound-toggle" aria-pressed={soundOn} onClick={onSound}>
              {soundOn ? <SpeakerHigh size={16} weight="fill" aria-hidden="true" /> : <SpeakerSlash size={16} weight="fill" aria-hidden="true" />}
              {soundOn ? "Sound on" : "Sound off"}
            </button>
          ) : garden ? (
            <>
              <button type="button" className="sign-in" onClick={openConnect}>Sign in</button>
              <button type="button" className="primary" onClick={showApp}>Grow your garden</button>
            </>
          ) : (
            <>
              <a className="sign-in" href="/auth/github" onClick={openConnect}>Sign in</a>
              <a className="primary" href="/auth/github" onClick={openConnect}>Grow your garden</a>
            </>
          )}
          {garden && !atHome ? (
            <span className="who">
              <span className="avatar" aria-hidden="true">{(garden.display_name || garden.login || "?").slice(0, 1).toUpperCase()}</span>
              <span className="mono">@{garden.login}</span>
            </span>
          ) : null}
        </div>
      </header>

      {offline ? <p className="banner offline" role="status">You're offline. Showing your garden as it was last loaded. Changes will sync when you're back.</p> : null}
      {garden && !atHome && status ? <p className="banner" role="status">{status}</p> : null}

      {garden && !atHome ? (
        <main id="content" className="page">
          {view === "collection" ? <Collection garden={garden} focusPlant={focusPlant} onOpen={setView} /> : null}
          {view === "journal" ? <Journal garden={garden} onOpen={setView} /> : null}
          {view === "settings" ? (
            <Settings
              garden={garden}
              themeChoice={themeChoice}
              onTheme={onTheme}
              soundOn={soundOn}
              onSound={onSound}
              repos={repos}
              onGitHub={openConnect}
              onToggleRepo={onToggleRepo}
              onSync={syncRepos}
              onShare={() => setView("share")}
              onDescribe={() => setDescribed((value) => !value)}
              described={described}
              summary={gardenSummary(garden)}
              status={status}
              onLogout={logout}
              onDeleted={logout}
            />
          ) : null}
          {view === "explore" ? <Explore garden={garden} onOpen={setView} /> : null}
          {view === "share" ? <Share garden={garden} /> : null}
          {view === "garden" ? (
            <Dashboard
              garden={garden}
              onOpen={setView}
              onVisit={(plant) => { setFocusPlant(plant); setView("collection"); }}
            />
          ) : null}
          {levelUp ? (
            <LevelUp
              garden={garden}
              onClose={dismissLevelUp}
              onShare={() => { dismissLevelUp(); setView("share"); }}
            />
          ) : null}
        </main>
      ) : gate === "connect" ? (
        <Connect
          phase={connectPhase}
          detail={note}
          githubReady={githubReady}
          githubSetup={githubSetup}
          onContinue={continueGitHub}
          onDemo={enterDemo}
          onRetry={() => setConnectPhase("ready")}
          onGarden={showApp}
        />
      ) : (
        <Marketing onDemo={enterDemo} onGitHub={openConnect} onEnter={showApp} hasGarden={Boolean(garden)} note={note} />
      )}

      {garden && !atHome ? (
        <nav className="tabbar" aria-label="Mobile">
          <button type="button" aria-current={gardenCurrent ? "page" : undefined} onClick={() => setView("garden")}><Plant size={20} weight={gardenCurrent ? "fill" : "regular"} aria-hidden="true" />Garden</button>
          <button type="button" aria-current={view === "collection" ? "page" : undefined} onClick={() => setView("collection")}><SquaresFour size={20} weight={view === "collection" ? "fill" : "regular"} aria-hidden="true" />Collection</button>
          <button type="button" aria-current={view === "journal" ? "page" : undefined} onClick={() => setView("journal")}><BookOpen size={20} weight={view === "journal" ? "fill" : "regular"} aria-hidden="true" />Journal</button>
          <button type="button" aria-current={view === "settings" ? "page" : undefined} onClick={() => setView("settings")}><Gear size={20} weight={view === "settings" ? "fill" : "regular"} aria-hidden="true" />Settings</button>
        </nav>
      ) : <SiteFooter onDemo={enterDemo} onGitHub={openConnect} />}
      <Toasts items={toasts} onDismiss={dismissToast} />
    </>
  );
}
