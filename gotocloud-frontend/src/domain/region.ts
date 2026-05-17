export interface Region {
  /** ISO 3166-1 alpha-2 code (used to fetch flag image) */
  code: string;
  /** Display name in Spanish */
  name: string;
  /** Optional subtitle like "Sede principal" */
  tag?: string;
}
