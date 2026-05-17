import type { FooterColumn, NavMenuItem, SocialLink } from "../../domain/nav";

export const PRIMARY_NAV: NavMenuItem[] = [
  {
    label: "Servicios",
    children: [
      { label: "Servicios en la Nube", href: "#cloud-computing" },
      { label: "Modernización de Aplicaciones", href: "#app-modernization" },
      { label: "Seguridad", href: "#seguridad" },
      { label: "Servicios Administrados", href: "#servicios-administrados" },
      { label: "Datos", href: "#data" },
      { label: "Soluciones SaaS", href: "#soluciones-saas" },
    ],
  },
  {
    label: "SaaS",
    children: [
      { label: "Karman", href: "#karman" },
      { label: "Oasis", href: "#oasis" },
      { label: "Dataloom", href: "#dataloom" },
    ],
  },
  {
    label: "Soluciones",
    children: [
      { label: "Descubrir", href: "#descubrir" },
      { label: "Tecnologías", href: "#tecnologias" },
      { label: "Nuestros Clientes", href: "#clientes" },
    ],
  },
  { label: "Nosotros", href: "#nosotros" },
  { label: "Trabaja con nosotros", href: "#trabaja" },
  { label: "Blog", href: "#blog" },
  { label: "Admin", href: "https://7r9fb398-5173.use.devtunnels.ms/dashboard", cta: true },
];

export const SOCIAL_LINKS: SocialLink[] = [
  { label: "LinkedIn", href: "https://www.linkedin.com/company/gotocloudsas", icon: "linkedin" },
  { label: "WhatsApp", href: "https://wa.me/573174270148", icon: "whatsapp" },
  { label: "YouTube", href: "https://www.youtube.com/@GoToCloudSAS", icon: "youtube" },
];

export const FOOTER_COLUMNS: FooterColumn[] = [
  {
    title: "Servicios",
    links: [
      { label: "Servicios en la nube", href: "#cloud-computing" },
      { label: "Modernización de aplicaciones", href: "#app-modernization" },
      { label: "Seguridad", href: "#seguridad" },
      { label: "Servicios Administrados", href: "#servicios-administrados" },
      { label: "Datos", href: "#data" },
      { label: "Soluciones SaaS", href: "#soluciones-saas" },
    ],
  },
  {
    title: "Soluciones",
    links: [
      { label: "Descubrir", href: "#descubrir" },
      { label: "Tecnologías", href: "#tecnologias" },
      { label: "Nuestros clientes", href: "#clientes" },
    ],
  },
  {
    title: "Soluciones SaaS",
    links: [
      { label: "Kármán Reporting Hub", href: "#karman" },
      { label: "OASIS AI", href: "#oasis" },
      { label: "DataLoom", href: "#dataloom" },
    ],
  },
  {
    title: "Trayectoria",
    links: [
      { label: "Acerca de nosotros", href: "#nosotros" },
      { label: "Trabaja con nosotros", href: "#trabaja" },
      { label: "Blog", href: "#blog" },
    ],
  },
];

export const FOOTER_LEGAL_LINKS: { label: string; href: string }[] = [
  { label: "Políticas empresariales", href: "#politicas" },
  { label: "Contáctenos", href: "#contacto" },
  { label: "Trabaja con nosotros", href: "#trabaja" },
  { label: "PQRS", href: "#pqrs" },
];

export const COPYRIGHT_TEXT = "All rights reserved GoToCloud 2025";
