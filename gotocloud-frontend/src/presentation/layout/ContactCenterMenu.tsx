import { getWhatsAppUrl } from "../../application/whatsapp";
import { MailIcon, PhoneIcon, SocialIcon } from "../../shared/ui/icons";
import "./ContactCenterButton.css";

type ContactCenterMenuProps = {
  id: string;
  onOpenChat: () => void;
  onOpenCall: () => void;
  onSelect: () => void;
};

function ContactCenterMenu({ id, onOpenChat, onOpenCall, onSelect }: ContactCenterMenuProps) {
  return (
    <div className="contact-center-menu" id={id} role="menu" aria-label="Opciones de contacto">
      <a
        className="contact-center-menu__item"
        href={getWhatsAppUrl({
          intent: "Contactar al equipo comercial de GoToCloud",
          detail: "Quiero recibir asesoría sobre soluciones cloud.",
          source: "gotocloud.com.co",
        })}
        target="_blank"
        rel="noopener noreferrer"
        aria-label="WhatsApp"
        title="WhatsApp"
        role="menuitem"
        onClick={onSelect}
      >
        <span className="contact-center-menu__label">WhatsApp</span>
        <SocialIcon icon="whatsapp" size={24} />
      </a>

      <button
        type="button"
        className="contact-center-menu__item"
        aria-label="Llamar a Camila"
        title="Llamar"
        role="menuitem"
        onClick={() => {
          onOpenCall();
          onSelect();
        }}
      >
        <span className="contact-center-menu__label">Llamar</span>
        <PhoneIcon size={24} />
      </button>

      <button
        type="button"
        className="contact-center-menu__item"
        aria-label="Correo"
        title="Correo"
        role="menuitem"
        onClick={() => {
          onOpenChat();
          onSelect();
        }}
      >
        <span className="contact-center-menu__label">Correo</span>
        <MailIcon size={24} />
      </button>
    </div>
  );
}

export default ContactCenterMenu;
