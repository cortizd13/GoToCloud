import { CONTACT_INFO, HERO_EMAIL } from "../infrastructure/data/contact.data";
import { REGIONS, getFlagUrl } from "../infrastructure/data/regions.data";

export const getContactSectionViewModel = () => ({
  hero: {
    title: "¡Conéctese con nuestro equipo de expertos!",
    description:
      "Estamos listos para ayudarle a implementar estos escenarios de Azure y Microsoft, impulsando la transformación de su negocio. Contáctenos para descubrir cómo podemos trabajar juntos en su proyecto de transformación digital y alcanzar el éxito.",
    email: HERO_EMAIL,
  },
  regions: {
    title: "Nuestra presencia regional",
    items: REGIONS.map((r) => ({ ...r, flag: getFlagUrl(r.code) })),
  },
  contact: {
    title: "¡Contáctenos!",
    info: CONTACT_INFO,
  },
});
