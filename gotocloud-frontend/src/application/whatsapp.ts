export const WHATSAPP_NUMBER = "573226787358";

type WhatsAppMessageInput = {
  intent: string;
  detail?: string;
  source?: string;
};

export function getWhatsAppUrl({ intent, detail, source = "gotocloud.com.co" }: WhatsAppMessageInput) {
  const message = [
    "Hola GoToCloud, quiero recibir asesoría.",
    `Estoy interesado en: ${intent}`,
    detail ? `Detalle: ${detail}` : null,
    "Me gustaría recibir orientación, alcance sugerido y próximos pasos.",
    `Origen: ${source}`
  ]
    .filter(Boolean)
    .join("\n");

  return `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(message)}`;
}
