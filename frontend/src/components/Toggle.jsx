export default function Toggle({ checked, disabled, onClick, label, busy }) {
  return (
    <button
      type="button"
      className="switch"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      aria-busy={busy || undefined}
      disabled={disabled}
      onClick={onClick}
    >
      <span className="switch-track" aria-hidden="true" />
      <span>{busy ? "…" : checked ? "On" : "Off"}</span>
    </button>
  );
}
