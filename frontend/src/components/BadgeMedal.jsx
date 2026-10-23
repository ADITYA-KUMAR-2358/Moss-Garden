import { ArrowCounterClockwise, LockSimple, Mountains } from "@phosphor-icons/react";
import { earnedDate } from "../badges.js";

const ICONS = { level: Mountains, return: ArrowCounterClockwise };

function Emblem({ badge }) {
  if (badge.art) {
    return <img className="medal-art" src={badge.isEarned ? badge.art : badge.off} alt="" draggable="false" />;
  }
  const Icon = ICONS[badge.icon] || Mountains;
  return <Icon className="medal-icon" weight={badge.isEarned ? "duotone" : "regular"} aria-hidden="true" />;
}

export default function BadgeMedal({ badge, size = "lg", details = true }) {
  const state = badge.isEarned ? "earned" : "locked";
  return (
    <figure className={`medal ${state} ${size}`}>
      <div className="medal-stage" aria-hidden="true">
        {badge.isEarned ? <span className="medal-rays" /> : null}
        <span className="medal-disc">
          <Emblem badge={badge} />
          {badge.isEarned ? <span className="medal-shine" /> : null}
        </span>
        {!badge.isEarned ? (
          <span className="medal-lock"><LockSimple size={12} weight="bold" /></span>
        ) : null}
      </div>
      <figcaption>
        <span className="medal-name">{badge.name}</span>
        {details ? <span className="medal-desc">{badge.isEarned ? badge.earned : badge.hint}</span> : null}
        <span className="medal-when">
          {badge.isEarned ? (
            <>Earned <time dateTime={badge.earnedOn}>{earnedDate(badge.earnedOn, size === "sm")}</time></>
          ) : (
            <><LockSimple size={11} weight="bold" aria-hidden="true" /> Still to unlock</>
          )}
        </span>
      </figcaption>
    </figure>
  );
}
