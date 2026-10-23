import { useState } from "react";
import { CaretDown, CaretUp, Check, LockSimple, Play, SpeakerSlash, X } from "@phosphor-icons/react";
import offToggle from "../art/toggle/off.svg";
import heroGarden from "../art/marketing/hero-garden.png";
import sprout from "../art/marketing/sprout.png";
import stages from "../art/marketing/stages.png";
import levelSeedbed from "../art/marketing/level-seedbed.png";
import levelUnderstory from "../art/marketing/level-understory.png";
import levelOldGrowth from "../art/marketing/level-old-growth.png";
import plantFern from "../art/marketing/plant-fern.png";
import plantMoss from "../art/marketing/plant-moss.png";
import plantAster from "../art/marketing/plant-aster.png";
import plantLantern from "../art/marketing/plant-lantern.png";
import plantCanopy from "../art/marketing/plant-canopy.png";

const STEPS = [
  {
    kind: "commit",
    kicker: "01 · Commit",
    title: "You push a small change.",
    body: "Any commit, pull request or review to a repository you connected counts. They are roughly equal units, so there is nothing to game.",
  },
  {
    kind: "grow",
    kicker: "02 · Grow",
    title: "The garden grows a little.",
    body: "XP plants seeds and helps them through four stages. A quiet week still moves things forward, just more slowly.",
  },
  {
    kind: "reflect",
    kicker: "03 · Reflect",
    title: "A journal notices what changed.",
    body: "Each week, a short entry describes what grew and where it came from. Written by an optional on-device model, or as a plain summary.",
  },
];

const LEVELS = [
  {
    art: levelSeedbed,
    alt: "A wide bowl of soil with four seedlings.",
    kicker: "Level 2 · Seedbed · March",
    title: "Four seedlings and room to grow.",
  },
  {
    art: levelUnderstory,
    alt: "A garden with ferns, a young maple, and a lantern bud.",
    kicker: "Level 7 · Understory · October",
    title: "Ferns, a young maple, the first lantern bud.",
  },
  {
    art: levelOldGrowth,
    alt: "A full garden with twelve plants, flowers, and a pocket maple.",
    kicker: "Level 14 · Old growth · Next autumn",
    title: "Twelve plants, three of them rare.",
  },
];

const PLANTS = [
  {
    art: plantFern,
    alt: "Hart's fern, mature.",
    name: "Afternoon",
    meta: "Hart’s fern · Mature",
    found: "Found 14 Oct · garden-api",
  },
  {
    art: plantMoss,
    alt: "Cushion moss, mature.",
    name: "Small Hours",
    meta: "Cushion moss · Mature",
    found: "Found 2 Sep · dotfiles",
  },
  {
    art: plantAster,
    alt: "Clay aster, young.",
    name: "Second Draft",
    meta: "Clay aster · Young",
    found: "Found 7 Oct · garden-api",
  },
  {
    art: plantLantern,
    alt: "",
    name: "Not yet found",
    meta: "Seasonal · Rare",
    found: "Something stirs here in late winter.",
    hidden: true,
  },
  {
    art: plantCanopy,
    alt: "",
    name: "Not yet found",
    meta: "Rare · Old growth",
    found: "Appears after a long, steady season.",
    hidden: true,
  },
];

const QUESTIONS = [
  ["What happens if I take a break?", "Nothing is lost. Lifetime XP stays where it is; only vitality settles. Your garden will be here when you return."],
  ["Does it count lines of code?", "No. Commits, pull requests and reviews count as small, roughly equal units, so there is no reason to pad your work."],
  ["Do I have to use the AI?", "No. It is off by default. Without it, plants get species names and the journal is a plain weekly summary."],
  ["Will it ever play sound on its own?", "Never. Audio is off by default and only plays when you press play."],
  ["Can I delete my garden?", "Yes, from Settings. You can export it first; deleting is permanent and asks you to confirm."],
];

export default function Marketing({ onDemo, onGitHub, onEnter, hasGarden, note }) {
  const [openQuestion, setOpenQuestion] = useState(0);
  const Start = hasGarden ? "button" : "a";
  const startProps = hasGarden
    ? { type: "button", onClick: onEnter }
    : { href: "/auth/github", onClick: onGitHub };

  return (
    <main id="content" className="page market">
      <section className="m-hero">
        <div className="m-hero-copy">
          <p className="m-kicker">A slow-productivity game for developers</p>
          <h1>
            <span>Small commits. Slow</span>
            <span>growth. A garden</span>
            <span>that remembers.</span>
          </h1>
          <p className="m-lede">
            Moss Garden turns your GitHub contributions into a miniature garden that keeps everything it grows. No streaks to protect, no countdowns, nothing to lose.
          </p>
          <div className="m-actions">
            <Start className="primary" {...startProps}>Grow your garden</Start>
            <button type="button" className="secondary" onClick={onDemo}>Explore a demo garden</button>
          </div>
          <p className="m-fine">Reads contribution activity only. Never your code.</p>
          {note ? <p className="note" role="status">{note}</p> : null}
        </div>
        <img
          className="m-hero-art"
          src={heroGarden}
          alt="A late-autumn garden. Autumn lantern, seasonal, level 11. Pocket maple, grew from 412 commits."
        />
      </section>

      <section className="m-section" id="how" aria-labelledby="how-title">
        <p className="m-kicker">How the garden grows</p>
        <h2 id="how-title">Commit. Grow. Reflect.</h2>
        <p className="m-intro">Three small things happen, at the pace you work. Nothing asks you to hurry.</p>
        <ol className="m-cards">
          {STEPS.map((step) => (
            <li key={step.kicker}>
              {step.kind === "commit" ? (
                <div className="m-panel m-terminal">
                  <p>garden-api · 21 Oct, 09:14</p>
                  <pre>{`$ git commit -m "fix: retry on 502"\n$ git push origin main`}</pre>
                  <p className="m-gain">→ garden-api · +40 XP</p>
                  <img src={sprout} alt="" />
                </div>
              ) : null}
              {step.kind === "grow" ? (
                <div className="m-panel m-stages">
                  <p>seed → sprout → young → mature</p>
                  <img src={stages} alt="A seed, a sprout, a young fern, and a mature fern." />
                </div>
              ) : null}
              {step.kind === "reflect" ? (
                <div className="m-panel m-preview">
                  <p>journal · 19 Oct</p>
                  <p className="m-kicker">Week 42</p>
                  <h3>The week the moss settled</h3>
                  <p>Three quiet days, then a long Thursday in garden-api. A lantern bud appeared near the front of the garden.</p>
                </div>
              ) : null}
              <p className="m-kicker">{step.kicker}</p>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="m-section" aria-labelledby="levels-title">
        <p className="m-kicker">A garden that remembers</p>
        <h2 id="levels-title">From seedbed to old growth.</h2>
        <p className="m-intro">
          Levels widen the soil and unlock species. Seasons change the light and bring rare plants. Nothing you grow is taken back.
        </p>
        <ol className="m-cards">
          {LEVELS.map((level) => (
            <li key={level.kicker}>
              <img src={level.art} alt={level.alt} />
              <p className="m-kicker">{level.kicker}</p>
              <p className="m-italic">{level.title}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="m-section" aria-labelledby="progress-title">
        <p className="m-kicker">Two kinds of progress</p>
        <h2 id="progress-title">What you have grown, and how it looks today.</h2>
        <div className="m-pair">
          <article>
            <div className="m-meter-label">
              <span>Lifetime XP</span>
              <span className="m-mono">2,340 / 2,800 XP</span>
            </div>
            <div className="m-track" aria-hidden="true"><span style={{ width: "83.6%" }} /></div>
            <p className="m-fine">Permanent. 460 XP until Level 8. It never goes down.</p>
            <h3>Lifetime XP is permanent.</h3>
            <p>Every contribution adds to it. It decides your level and which plants can appear. It never goes down, not after a holiday, not after a hard month.</p>
          </article>
          <article>
            <div className="m-meter-label">
              <span>Garden vitality</span>
              <span className="m-mono">Steady · 68%</span>
            </div>
            <div className="m-track clay" aria-hidden="true"><span style={{ width: "68%" }} /></div>
            <p className="m-fine">Temporary. Rises with activity, rests when you do.</p>
            <h3>Vitality is temporary.</h3>
            <p>It reflects the last few weeks: the surface gets a little brighter when you are active and settles when you rest. Plants never wilt, and vitality never costs you anything.</p>
          </article>
        </div>
      </section>

      <section className="m-rest">
        <div>
          <p className="m-kicker">Breaks never reset</p>
          <h2>Nothing lost. Just room to grow.</h2>
        </div>
        <div>
          <p>Take a week off, or a month. When you come back, your garden is exactly where you left it, with a short note about the time away.</p>
          <p>There are no streaks, no timers and no “you’re about to lose” emails. Your garden will be here when you return.</p>
        </div>
      </section>

      <section className="m-section m-journal" id="journal" aria-labelledby="journal-title">
        <div>
          <p className="m-kicker">The weekly journal</p>
          <h2 id="journal-title">A few calm paragraphs about your week.</h2>
          <p>It notices what grew and where it came from. It never grades you. Narration is optional, off by default, and always comes with the text.</p>
        </div>
        <article>
          <p className="m-kicker">Week 42 · 13–19 October · Late autumn</p>
          <h3>The week the moss settled</h3>
          <p>Three quiet days, then a long Thursday in garden-api. Most of the work was small: a retry for a flaky request, a clearer error message, one test that had been skipped for months.</p>
          <p>The moss cushion by the stones filled in at its edges. Near the front, a lantern bud appeared, the first sign of late autumn. It will open when it is ready.</p>
          <div className="m-listen-row">
            <button type="button" className="m-listen" disabled>
              <Play size={14} weight="fill" aria-hidden="true" />
              Listen · 3:40
            </button>
            <p>Sound is off until you press play. Transcript is the text above.</p>
          </div>
        </article>
      </section>

      <section className="m-section" aria-labelledby="collection-title">
        <div className="m-collection-lead">
          <div>
            <p className="m-kicker">The collection</p>
            <h2 id="collection-title">Some plants only arrive in certain seasons.</h2>
            <p>Every plant you grow is kept in a field journal. Rare ones stay hidden until their season. No checklists, no timers.</p>
          </div>
          <p className="m-meta">6 species · 24 growth stages · seasonal rarities</p>
        </div>
        <ul className="m-plants">
          {PLANTS.map((plant) => (
            <li key={plant.meta}>
              <img src={plant.art} alt={plant.alt} />
              <p className="m-italic">
                {plant.hidden ? <LockSimple size={14} weight="regular" aria-hidden="true" /> : null}
                {plant.name}
              </p>
              <p className="m-meta">{plant.meta}</p>
              <p className="m-fine">{plant.found}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="m-section" id="model" aria-labelledby="optional-title">
        <p className="m-kicker">Optional, and off until you say so</p>
        <h2 id="optional-title">A gardener and a little sound, if you want them.</h2>
        <div className="m-pair m-ruled">
          <article>
            <div className="m-row">
              <h3>AI gardener</h3>
              <span className="m-switch">
                <img src={offToggle} alt="" width={36} height={20} />
                Off
              </span>
            </div>
            <p>An open-weight model names new plants and writes the weekly journal. It runs on your device; nothing about your work is sent to a hosted AI service. When it is off, you get plain, accurate summaries instead.</p>
            <p className="m-meta">open-weight · on-device · optional</p>
          </article>
          <article>
            <div className="m-row">
              <h3>Sound &amp; narration</h3>
              <span className="m-sound-pill">
                <SpeakerSlash size={16} aria-hidden="true" />
                Sound off
              </span>
            </div>
            <p>Soft ambient sound and a narrated journal are available, but audio is off by default and never autoplays. Every narration has a full transcript.</p>
            <p className="m-meta">off by default · never autoplays · transcripts always</p>
          </article>
        </div>
      </section>

      <section className="m-section m-privacy" id="privacy" aria-labelledby="privacy-title">
        <div>
          <p className="m-kicker">Privacy &amp; GitHub permissions</p>
          <h2 id="privacy-title">Your garden needs very little.</h2>
          <p>Moss Garden asks GitHub for read-only access to contribution activity. You choose which repositories count, and you can disconnect at any time.</p>
          <p className="m-fine">Requested scope: <span className="m-mono">read:user</span> (read-only)</p>
        </div>
        <div>
          <h3>We read</h3>
          <ul className="m-checks">
            {["Contribution counts and dates", "Names of repositories you choose to include", "Your public profile name and avatar"].map((item) => (
              <li key={item}><Check size={16} weight="bold" aria-hidden="true" />{item}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3>We never</h3>
          <ul className="m-checks never">
            {["Read or store the contents of your code", "Write to GitHub or post on your behalf", "Share your activity with anyone"].map((item) => (
              <li key={item}><X size={16} aria-hidden="true" />{item}</li>
            ))}
          </ul>
        </div>
      </section>

      <section className="m-section m-faq" id="faq" aria-labelledby="faq-title">
        <div>
          <p className="m-kicker">Open by design</p>
          <h2 id="faq-title">Questions, answered plainly.</h2>
          <p>The plant-naming model is open-weight, so you can see what it is and run it yourself. Your garden can be exported as a documented file at any time.</p>
        </div>
        <div className="m-accordion">
          {QUESTIONS.map(([question, answer], index) => {
            const open = openQuestion === index;
            return (
              <div className={open ? "open" : ""} key={question}>
                <button
                  type="button"
                  aria-expanded={open}
                  onClick={() => setOpenQuestion(open ? -1 : index)}
                >
                  <span>{question}</span>
                  {open ? <CaretUp size={16} aria-hidden="true" /> : <CaretDown size={16} aria-hidden="true" />}
                </button>
                {open ? <p>{answer}</p> : null}
              </div>
            );
          })}
        </div>
      </section>

      <section className="m-close">
        <p className="m-kicker">Start with one small commit</p>
        <h2>Grow something that stays.</h2>
        <div className="m-actions">
          <Start className="primary" {...startProps}>Grow your garden</Start>
          <button type="button" className="m-text-link" onClick={onDemo}>Explore a demo garden</button>
        </div>
      </section>
    </main>
  );
}
