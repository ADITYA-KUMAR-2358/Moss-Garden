import { Check, Info, Plant, Warning, X } from "@phosphor-icons/react";

const ICONS = {
  plant: Plant,
  ok: Check,
  info: Info,
  warn: Warning,
};

export default function Toasts({ items, onDismiss }) {
  if (!items.length) return null;
  return (
    <div className="toasts" aria-live="polite">
      {items.map((item) => {
        const Icon = ICONS[item.tone] || Info;
        return (
          <div className={`toast toast-${item.tone || "info"}`} key={item.id} role="status">
            <Icon size={16} weight={item.tone === "plant" ? "fill" : "bold"} aria-hidden="true" />
            <p>{item.message}</p>
            {item.actionLabel ? (
              <button type="button" className="toast-action" onClick={() => { item.action?.(); onDismiss(item.id); }}>
                {item.actionLabel}
              </button>
            ) : null}
            <button type="button" className="toast-close" aria-label="Dismiss" onClick={() => onDismiss(item.id)}>
              <X size={14} aria-hidden="true" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
