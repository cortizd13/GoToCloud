# CLAUDE.md

## Objetivo
Réplica visual estática (React) de https://www.gotocloud.ai/contacto-servicios-cloud/
— solo frontend, demo visual.

Cubre: **Header con navegación + dropdowns**, **sección de contactos** (hero,
presencia regional, bloque teléfono/dirección/correo) y **Footer corporativo**
con 4 columnas + barra inferior legal.

## Stack
- React 19 + TypeScript
- Vite
- CSS plano + design tokens (sin Tailwind, sin librerías de UI)
- Banderas: flagcdn.com (SVG remoto, sin deps)
- Iconos y logo: SVG inline propios

## Restricciones
- Solo frontend. Sin backend, auth ni formularios funcionales.
- Sin dependencias nuevas salvo necesidad clara.
- Contenido estático separado de componentes.
- Dropdowns y drawer móvil 100% client-side (useState).

## Variables de entorno
Ninguna.

## Comandos de validación
```bash
npm install
npm run lint        # ESLint
npm run build       # tsc -b && vite build  (typecheck + bundle)
npm run dev         # local
```

## Arquitectura
```
src/
├── domain/                       # tipos puros
│   ├── nav.ts                    # NavMenuItem, SocialLink, FooterColumn
│   ├── contact.ts
│   └── region.ts
├── infrastructure/data/          # mocks estáticos
│   ├── nav.data.ts               # PRIMARY_NAV, SOCIAL_LINKS, FOOTER_COLUMNS...
│   ├── contact.data.ts
│   └── regions.data.ts
├── application/
│   └── contactSection.ts
├── presentation/
│   ├── layout/                   # chrome del sitio
│   │   ├── Header.tsx + .css
│   │   ├── Footer.tsx + .css
│   │   └── SiteLayout.tsx
│   └── sections/
│       └── ContactSection.tsx + .css
├── shared/
│   ├── styles/
│   │   ├── tokens.css
│   │   └── global.css
│   └── ui/
│       ├── icons.tsx
│       └── Logo.tsx + .css
├── App.tsx
└── main.tsx
```

## Definición de terminado
- `npm run build` sin errores (typecheck + bundle).
- `npm run lint` sin errores propios.
- Header sticky con dropdowns en desktop y drawer en mobile.
- Footer dark con 4 columnas en desktop, 2 en mobile, barra legal abajo.
- Sección de contacto fiel al original en composición y tono.
- Responsive validado en ≥1024 px y ≤480 px.
