import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

const base = (size: number) => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  fill: "currentColor",
  xmlns: "http://www.w3.org/2000/svg",
  "aria-hidden": true,
});

export function LinkedInIcon({ size = 18, ...rest }: IconProps) {
  return (
    <svg {...base(size)} {...rest}>
      <path d="M4.98 3.5a2.5 2.5 0 1 1 .02 5 2.5 2.5 0 0 1-.02-5zM3 9.5h4V21H3V9.5zM10 9.5h3.8v1.6h.05c.53-.96 1.83-1.97 3.77-1.97 4.03 0 4.78 2.5 4.78 5.74V21h-4v-5.36c0-1.28-.02-2.92-1.84-2.92-1.85 0-2.13 1.36-2.13 2.83V21h-4V9.5z" />
    </svg>
  );
}

export function WhatsAppIcon({ size = 18, ...rest }: IconProps) {
  return (
    <svg {...base(size)} {...rest}>
      <path d="M19.05 4.91A10.05 10.05 0 0 0 12 2C6.48 2 2 6.48 2 12c0 1.76.46 3.45 1.32 4.95L2 22l5.18-1.36A9.93 9.93 0 0 0 12 22c5.52 0 10-4.48 10-10 0-2.67-1.04-5.18-2.95-7.09zM12 20.13a8.12 8.12 0 0 1-4.14-1.14l-.3-.18-3.07.8.82-3-.19-.31A8.13 8.13 0 1 1 20.13 12c0 4.49-3.64 8.13-8.13 8.13zm4.47-6.1c-.24-.12-1.45-.72-1.67-.8-.22-.08-.39-.12-.55.12-.16.24-.63.8-.77.97-.14.16-.28.18-.52.06-.24-.12-1.03-.38-1.97-1.21-.73-.65-1.22-1.45-1.36-1.69-.14-.24-.02-.37.1-.49.1-.1.24-.28.36-.42.12-.14.16-.24.24-.4.08-.16.04-.3-.02-.42-.06-.12-.55-1.32-.75-1.81-.2-.48-.4-.41-.55-.42h-.47c-.16 0-.42.06-.64.3-.22.24-.84.82-.84 2s.86 2.32.98 2.48c.12.16 1.69 2.58 4.1 3.62.57.25 1.02.4 1.37.51.57.18 1.09.16 1.5.1.46-.07 1.45-.59 1.66-1.16.2-.57.2-1.06.14-1.16-.06-.1-.22-.16-.46-.28z" />
    </svg>
  );
}

export function YouTubeIcon({ size = 18, ...rest }: IconProps) {
  return (
    <svg {...base(size)} {...rest}>
      <path d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.6 3.6 12 3.6 12 3.6s-7.6 0-9.4.5A3 3 0 0 0 .5 6.2C0 8 0 12 0 12s0 4 .5 5.8a3 3 0 0 0 2.1 2.1c1.8.5 9.4.5 9.4.5s7.6 0 9.4-.5a3 3 0 0 0 2.1-2.1c.5-1.8.5-5.8.5-5.8s0-4-.5-5.8zM9.6 15.5V8.5l6.3 3.5-6.3 3.5z" />
    </svg>
  );
}

export function PhoneIcon({ size = 22, ...rest }: IconProps) {
  return (
    <svg {...base(size)} {...rest}>
      <path d="M6.6 10.8c1.4 2.8 3.8 5.1 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.3 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1-9.4 0-17-7.6-17-17 0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.2.2 2.4.6 3.6.1.4 0 .7-.3 1l-2.2 2.2z" />
    </svg>
  );
}

export function MapPinIcon({ size = 22, ...rest }: IconProps) {
  return (
    <svg {...base(size)} {...rest}>
      <path d="M12 2C8 2 5 5 5 9c0 5.3 7 13 7 13s7-7.7 7-13c0-4-3-7-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z" />
    </svg>
  );
}

export function MailIcon({ size = 22, ...rest }: IconProps) {
  return (
    <svg {...base(size)} {...rest}>
      <path d="M3 5h18c.6 0 1 .4 1 1v12c0 .6-.4 1-1 1H3c-.6 0-1-.4-1-1V6c0-.6.4-1 1-1zm9 7.5L20 7H4l8 5.5zM4 18h16V9.2l-7.4 5a1 1 0 0 1-1.2 0L4 9.2V18z" />
    </svg>
  );
}

export function ChevronDownIcon({ size = 14, ...rest }: IconProps) {
  return (
    <svg {...base(size)} {...rest}>
      <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </svg>
  );
}

export function MenuIcon({ size = 24, ...rest }: IconProps) {
  return (
    <svg {...base(size)} {...rest}>
      <path d="M3 6h18M3 12h18M3 18h18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" fill="none" />
    </svg>
  );
}

export function CloseIcon({ size = 24, ...rest }: IconProps) {
  return (
    <svg {...base(size)} {...rest}>
      <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" fill="none" />
    </svg>
  );
}

export function ArrowRightIcon({ size = 16, ...rest }: IconProps) {
  return (
    <svg {...base(size)} {...rest}>
      <path d="M5 12h14M13 5l7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </svg>
  );
}

export const SocialIcon = ({ icon, ...rest }: { icon: "linkedin" | "whatsapp" | "youtube" } & IconProps) => {
  switch (icon) {
    case "linkedin": return <LinkedInIcon {...rest} />;
    case "whatsapp": return <WhatsAppIcon {...rest} />;
    case "youtube":  return <YouTubeIcon {...rest} />;
  }
};
