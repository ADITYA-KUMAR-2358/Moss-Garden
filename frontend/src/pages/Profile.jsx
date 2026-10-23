import { useState } from "react";
import { ArrowSquareOut, Gear, GithubLogo, ShareNetwork, SignOut } from "@phosphor-icons/react";
import { levelName, SEASONS } from "../components/Dashboard.jsx";
import { PlantMark, vitalityBand } from "../components/GardenScene.jsx";
import BadgeMedal from "../components/BadgeMedal.jsx";
import { badgeStates } from "../badges.js";

const DATE = new Intl.DateTimeFormat("en", { day: "numeric", month: "short", year: "numeric" });
const MONTH = new Intl.DateTimeFormat("en", { month: "long", year: "numeric" });

function readDay(iso) {
  if (!iso) return null;
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export function Avatar({ garden, size = 32 }) {
  const [failed, setFailed] = useState(false);
  const src = garden.profile?.avatar_url;
  const initial = (garden.display_name || garden.login || "?").slice(0, 1).toUpperCase();
  if (src && !failed) {
    return (
      <img
        className="avatar"
        src={src}
        alt=""
        width={size}
        height={size}
        style={{ width: size, height: size }}
        onError={() => setFailed(true)}
      />
    );
  }
  return (
    <span className="avatar" aria-hidden="true" style={{ width: size, height: size, fontSize: Math.round(size * 0.38) }}>
      {initial}
    </span>
  );
}

export default function Profile({ garden, onOpen, onLogout }) {
  const profile = garden.profile || {};
  const since = readDay(profile.member_since);
  const firstDay = readDay(profile.first_commit_day);
  const progress = garden.next_level_xp ? Math.min(100, Math.round((garden.xp / garden.next_level_xp) * 100)) : 100;
  const remaining = garden.next_level_xp ? Math.max(garden.next_level_xp - garden.xp, 0) : 0;
  const plants = garden.plants || [];
  const recentPlants = plants.slice(-6).reverse();
  const allBadges = badgeStates(garden);
  const badges = [...allBadges.filter((badge) => badge.isEarned), ...allBadges.filter((badge) => !badge.isEarned)];
  const earnedCount = allBadges.filter((badge) => badge.isEarned).length;

  const stats = [
    ["Lifetime XP", garden.xp.toLocaleString("en")],
    ["Commits counted", (profile.commits ?? 0).toLocaleString("en")],
    ["Active days", (profile.active_days ?? 0).toLocaleString("en")],
    ["Plants", plants.length],
    ["Badges", (garden.badges || []).length],
    ["Repositories", garden.demo ? "Demo" : profile.repos ?? 0],
  ];

  return (
    <section className="sheet profile" aria-labelledby="profile-title">
      <p className="overline">Profile</p>

      <div className="profile-grid">
        <article className="profile-card">
          <Avatar garden={garden} size={96} />
          <div className="profile-id">
            <h1 id="profile-title" className="profile-name">{garden.display_name || garden.login}</h1>
            <p className="mono profile-login">@{garden.login}</p>
            {garden.demo ? <span className="profile-tag">Demo garden</span> : null}
          </div>
          <dl className="profile-facts">
            {since ? (
              <div>
                <dt>Gardening since</dt>
                <dd>{MONTH.format(since)}</dd>
              </div>
            ) : null}
            {firstDay ? (
              <div>
                <dt>First commit counted</dt>
                <dd>{DATE.format(firstDay)}</dd>
              </div>
            ) : null}
            <div>
              <dt>Season</dt>
              <dd>{SEASONS[garden.season] || garden.season}</dd>
            </div>
            <div>
              <dt>Garden feels</dt>
              <dd>{vitalityBand(garden.vitality)}</dd>
            </div>
          </dl>
          <div className="profile-actions">
            {profile.github_url ? (
              <a className="secondary" href={profile.github_url} target="_blank" rel="noopener noreferrer">
                <GithubLogo size={18} weight="fill" aria-hidden="true" />
                GitHub profile
                <ArrowSquareOut size={14} aria-hidden="true" />
              </a>
            ) : null}
            <button type="button" className="secondary" onClick={() => onOpen("share")}>
              <ShareNetwork size={18} aria-hidden="true" />
              Share card
            </button>
            <button type="button" className="secondary" onClick={() => onOpen("settings")}>
              <Gear size={18} aria-hidden="true" />
              Settings
            </button>
            <button type="button" className="text-link profile-logout" onClick={onLogout}>
              <SignOut size={18} aria-hidden="true" />
              Log out
            </button>
          </div>
        </article>

        <div className="profile-main">
          <article className="profile-level">
            <header>
              <p className="profile-level-name">
                Lv {garden.level} <em>{levelName(garden.level)}</em>
              </p>
              <p className="caption">
                {garden.next_level_xp
                  ? `${remaining.toLocaleString("en")} XP to ${levelName(garden.level + 1)}`
                  : "Highest level reached"}
              </p>
            </header>
            <div
              className="track"
              role="progressbar"
              aria-label="Progress to the next level"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={progress}
            >
              <span style={{ width: `${progress}%` }} />
            </div>
          </article>

          <dl className="profile-stats">
            {stats.map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>

          <article className="profile-block">
            <header>
              <h2>Badges <span className="caption">{earnedCount} of {badges.length}</span></h2>
              <button type="button" className="text-link" onClick={() => onOpen("collection")}>See all</button>
            </header>
            <ul className="medal-grid compact">
              {badges.map((badge) => (
                <li key={badge.id}><BadgeMedal badge={badge} size="sm" details={false} /></li>
              ))}
            </ul>
          </article>

          <article className="profile-block">
            <header>
              <h2>Recently grown</h2>
              <button type="button" className="text-link" onClick={() => onOpen("collection")}>Collection</button>
            </header>
            {recentPlants.length ? (
              <ul className="profile-plants">
                {recentPlants.map((plant) => (
                  <li key={plant.slot}>
                    <PlantMark species={plant.species} stage={plant.stage} size={96} />
                    <span className="profile-plant-name">{plant.name}</span>
                    <span className="caption">{plant.label} · {plant.stage}</span>
                  </li>
                ))}
              </ul>
            ) : <p className="caption">A bare patch of soil, for now.</p>}
          </article>
        </div>
      </div>
    </section>
  );
}
