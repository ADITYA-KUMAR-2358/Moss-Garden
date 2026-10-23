import { useEffect, useId, useRef, useState } from "react";
import { List, X } from "@phosphor-icons/react";

export default function MobileMenu({ className = "", children }) {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef(null);
  const panelRef = useRef(null);
  const panelId = useId();

  useEffect(() => {
    if (!open) return undefined;
    panelRef.current?.querySelector("a, button")?.focus();

    function onKey(event) {
      if (event.key !== "Escape") return;
      setOpen(false);
      buttonRef.current?.focus();
    }
    function onPointer(event) {
      if (panelRef.current?.contains(event.target) || buttonRef.current?.contains(event.target)) return;
      setOpen(false);
    }
    function onResize() {
      if (buttonRef.current && getComputedStyle(buttonRef.current).display === "none") setOpen(false);
    }
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer);
    window.addEventListener("resize", onResize);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer);
      window.removeEventListener("resize", onResize);
    };
  }, [open]);

  function onPanelClick(event) {
    if (event.target.closest("a, button")) setOpen(false);
  }

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        className={`menu-toggle ${className}`.trim()}
        aria-expanded={open}
        aria-controls={panelId}
        aria-label={open ? "Close menu" : "Open menu"}
        onClick={() => setOpen((value) => !value)}
      >
        {open ? <X size={20} weight="bold" aria-hidden="true" /> : <List size={20} weight="bold" aria-hidden="true" />}
      </button>
      <div
        ref={panelRef}
        id={panelId}
        className={`menu-panel ${className}`.trim()}
        hidden={!open}
        onClick={onPanelClick}
      >
        {children}
      </div>
    </>
  );
}
