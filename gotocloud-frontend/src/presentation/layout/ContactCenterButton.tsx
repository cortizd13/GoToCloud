import { useEffect, useId, useRef, useState } from "react";
import { MdSupportAgent } from "react-icons/md";
import { CloseIcon } from "../../shared/ui/icons";
import "./ContactCenterButton.css";
import ChatbotWidget from "./ChatbotWidget";
import ContactCenterMenu from "./ContactCenterMenu";

function ContactCenterButton() {
  const [open, setOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const menuId = useId();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    const closeWithEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };

    const closeWhenClickingOutside = (event: PointerEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    document.addEventListener("keydown", closeWithEscape);
    document.addEventListener("pointerdown", closeWhenClickingOutside);

    return () => {
      document.removeEventListener("keydown", closeWithEscape);
      document.removeEventListener("pointerdown", closeWhenClickingOutside);
    };
  }, [open]);

  return (
    <div className={`contact-center${open ? " is-open" : ""}`} ref={containerRef}>
      {chatOpen && <ChatbotWidget onClose={() => setChatOpen(false)} />}
      {open && (
        <ContactCenterMenu
          id={menuId}
          onOpenChat={() => {
            setOpen(false);
            setChatOpen(true);
          }}
          onSelect={() => setOpen(false)}
        />
      )}

      <button
        type="button"
        className="contact-center-button"
        aria-controls={open ? menuId : undefined}
        aria-expanded={open}
        aria-label={open ? "Cerrar centro de contacto" : "Abrir centro de contacto"}
        onClick={() => {
          setChatOpen(false);
          setOpen((isOpen) => !isOpen);
        }}
      >
        {open ? <CloseIcon size={30} /> : <MdSupportAgent size={32} />}
      </button>
    </div>
  );
}

export default ContactCenterButton;
