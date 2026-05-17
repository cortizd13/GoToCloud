import type { Region } from "../../domain/region";

export const REGIONS: Region[] = [
  { code: "co", name: "Colombia", tag: "Sede principal" },
  { code: "us", name: "Estados Unidos" },
  { code: "ec", name: "Ecuador" },
  { code: "cl", name: "Chile" },
  { code: "ar", name: "Argentina" },
  { code: "gt", name: "Centroamérica" },
  { code: "mx", name: "México" },
  { code: "pe", name: "Perú" },
];

/** Returns a high-quality SVG flag URL from flagcdn (no extra deps required) */
export const getFlagUrl = (code: string): string =>
  `https://flagcdn.com/${code}.svg`;
