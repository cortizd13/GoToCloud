import "./Logo.css";

interface LogoProps {
  variant?: "light" | "dark";
  size?: "sm" | "md";
}

/**
 * Marca GoToCloud reconstruida como SVG inline (no hay asset oficial accesible).
 * variant="light" -> texto navy (sobre fondo claro)
 * variant="dark"  -> texto blanco (sobre fondo oscuro)
 */
export function Logo({ variant = "light", size = "md" }: LogoProps) {
  const textColor = variant === "light" ? "#0f2747" : "#ffffff";
  const subColor = variant === "light" ? "#64748b" : "#aebfd6";
  const accent = "#16a4d6";

  return (
    <span className={`gtc-logo gtc-logo--${size}`} aria-label="GoToCloud">
      <svg viewBox="0 0 220 44" xmlns="http://www.w3.org/2000/svg" role="img" aria-hidden="true">
        {/* Mark: cloud + up-chevron */}
        <g>
          <path
            d="M14 28c-5 0-9-3.6-9-8.2 0-4 3-7.4 7-8.1.7-4 4.1-7 8.2-7 3.2 0 6 1.8 7.4 4.5 1-.3 2-.5 3.1-.5 5 0 9 3.9 9 8.7 0 5.1-4.2 9-9.3 9H14z"
            fill={accent} opacity="0.18"
          />
          <path
            d="M16 22c-3.3 0-6-2.4-6-5.5 0-2.7 2-5 4.7-5.4.5-2.7 2.7-4.7 5.5-4.7 2.1 0 4 1.2 4.9 3 .7-.2 1.3-.3 2-.3 3.4 0 6.1 2.6 6.1 5.8 0 3.4-2.8 6.1-6.2 6.1H16z"
            fill={accent}
          />
          <path d="M19 18l4-4 4 4" stroke="#ffffff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" fill="none" />
        </g>
        {/* Wordmark */}
        <g fontFamily="Inter, Segoe UI, sans-serif">
          <text x="48" y="22" fontSize="18" fontWeight="700" letterSpacing="-0.4" fill={textColor}>GoTo</text>
          <text x="92" y="22" fontSize="18" fontWeight="400" letterSpacing="-0.4" fill={accent}>Cloud</text>
          <text x="48" y="36" fontSize="7.5" fontWeight="500" letterSpacing="3" fill={subColor}>CLOUD &nbsp;SERVICES</text>
        </g>
      </svg>
    </span>
  );
}
