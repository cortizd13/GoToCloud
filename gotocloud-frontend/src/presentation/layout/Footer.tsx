import {
  COPYRIGHT_TEXT,
  FOOTER_COLUMNS,
  FOOTER_LEGAL_LINKS,
  SOCIAL_LINKS,
} from "../../infrastructure/data/nav.data";
import { Logo } from "../../shared/ui/Logo";
import { SocialIcon } from "../../shared/ui/icons";
import "./Footer.css";

export function Footer() {
  return (
    <footer className="gtc-footer">
      <div className="container gtc-footer__top">
        <div className="gtc-footer__brand">
          <a href="#top" aria-label="GoToCloud — inicio">
            <Logo variant="dark" />
          </a>
          <p className="gtc-footer__tagline">
            Impulsamos la transformación digital con soluciones tecnológicas
            de vanguardia.
          </p>
          <div className="gtc-footer__social" aria-label="Redes sociales">
            {SOCIAL_LINKS.map((s) => (
              <a
                key={s.icon}
                href={s.href}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={s.label}
              >
                <SocialIcon icon={s.icon} size={18} />
              </a>
            ))}
          </div>
        </div>

        <div className="gtc-footer__cols">
          {FOOTER_COLUMNS.map((col) => (
            <div key={col.title} className="gtc-footer__col">
              <h4 className="gtc-footer__col-title">{col.title}</h4>
              <ul className="gtc-footer__col-list">
                {col.links.map((l) => (
                  <li key={l.href}>
                    <a href={l.href} className="gtc-footer__col-link">
                      {l.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      <div className="gtc-footer__bottom">
        <div className="container gtc-footer__bottom-inner">
          <ul className="gtc-footer__legal">
            {FOOTER_LEGAL_LINKS.map((l) => (
              <li key={l.href}>
                <a href={l.href}>{l.label}</a>
              </li>
            ))}
          </ul>
          <p className="gtc-footer__copyright">{COPYRIGHT_TEXT}</p>
        </div>
      </div>
    </footer>
  );
}
