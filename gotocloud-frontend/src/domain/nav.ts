export interface NavLink {
  label: string;
  href: string;
}

export interface NavMenuItem {
  label: string;
  href?: string;
  /** Si tiene children, es dropdown */
  children?: NavLink[];
  /** Marca el item como destacado tipo CTA (ej. "Contacto") */
  cta?: boolean;
}

export interface SocialLink {
  label: string;
  href: string;
  icon: "linkedin" | "whatsapp" | "youtube";
}

export interface FooterColumn {
  title: string;
  links: NavLink[];
}
