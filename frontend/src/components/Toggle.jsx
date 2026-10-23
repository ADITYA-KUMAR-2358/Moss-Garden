import { useState } from "react";
import off from "../art/toggle/off.svg";
import offFocus from "../art/toggle/off-focus.svg";
import offDisabled from "../art/toggle/off-disabled.svg";
import on from "../art/toggle/on.svg";
import onFocus from "../art/toggle/on-focus.svg";
import onDisabled from "../art/toggle/on-disabled.svg";

export default function Toggle({ checked, disabled, onClick, label }) {
  const [focused, setFocused] = useState(false);
  const art = disabled
    ? (checked ? onDisabled : offDisabled)
    : focused
      ? (checked ? onFocus : offFocus)
      : (checked ? on : off);
  const ring = focused && !disabled;

  return (
    <button
      type="button"
      className="toggle"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={onClick}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
    >
      <img src={art} alt="" width={ring ? 40 : 36} height={ring ? 24 : 20} />
      <span>{checked ? "On" : "Off"}</span>
    </button>
  );
}
