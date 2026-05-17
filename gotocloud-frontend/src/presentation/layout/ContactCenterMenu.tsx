import { getWhatsAppUrl } from "../../application/whatsapp";
import { CONTACT_INFO } from "../../infrastructure/data/contact.data";
import { MailIcon, PhoneIcon, SocialIcon } from "../../shared/ui/icons";
import "./ContactCenterButton.css";

type ContactCenterMenuProps = {
  id: string;
  onOpenChat: () => void;
  onSelect: () => void;
};

const contactActions = [
  {
    label: "WhatsApp",
    href: getWhatsAppUrl({
      intent: "Contactar al equipo comercial de GoToCloud",
      detail: "Quiero recibir asesoría sobre soluciones cloud.",
      source: "gotocloud.com.co",
    }),
    icon: <SocialIcon icon="whatsapp" size={24} />,
    external: true,
  },
  {
    label: "Llamar",
    href: CONTACT_INFO.phoneHref,
    icon: <PhoneIcon size={24} />,
  },
];

function ContactCenterMenu({ id, onOpenChat, onSelect }: ContactCenterMenuProps) {
  return (
    <div className="contact-center-menu" id={id} role="menu" aria-label="Opciones de contacto">
      {contactActions.map((action) => (
        <a
          key={action.label}
          className="contact-center-menu__item"
          href={action.href}
          target={action.external ? "_blank" : undefined}
          rel={action.external ? "noopener noreferrer" : undefined}
          aria-label={action.label}
          title={action.label}
          role="menuitem"
          onClick={onSelect}
        >
          <span className="contact-center-menu__label">{action.label}</span>
          {action.icon}
        </a>
      ))}

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
