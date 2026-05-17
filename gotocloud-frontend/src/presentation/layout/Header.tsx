import { useEffect, useState } from "react";
import { PRIMARY_NAV, SOCIAL_LINKS } from "../../infrastructure/data/nav.data";
import type { NavMenuItem } from "../../domain/nav";
import { Logo } from "../../shared/ui/Logo";
import { ChevronDownIcon, CloseIcon, MenuIcon, SocialIcon } from "../../shared/ui/icons";
import "./Header.css";

export function Header() {
  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);

  // Lock scroll when mobile drawer is open
  useEffect(() => {
    document.body.style.overflow = mobileOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [mobileOpen]);

  // Close mobile drawer with Esc
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { setMobileOpen(false); setOpenMenu(null); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const renderDesktopItem = (item: NavMenuItem) => {
    const isOpen = openMenu === item.label;
    if (item.children) {
      return (
        <li
          key={item.label}
          className={`gtc-nav__item gtc-nav__item--has-menu${isOpen ? " is-open" : ""}`}
          onMouseEnter={() => setOpenMenu(item.label)}
          onMouseLeave={() => setOpenMenu(null)}
        >
          <button
            type="button"
            className="gtc-nav__link gtc-nav__trigger"
            aria-expanded={isOpen}
            aria-haspopup="true"
            onClick={() => setOpenMenu(isOpen ? null : item.label)}
          >
            {item.label}
            <ChevronDownIcon size={12} />
          </button>
          <div className="gtc-nav__dropdown" role="menu">
            <ul>
              {item.children.map((c) => (
                <li key={c.href}>
                  <a className="gtc-nav__dropdown-link" href={c.href} role="menuitem">{c.label}</a>
                </li>
              ))}
            </ul>
          </div>
        </li>
      );
    }
    return (
      <li key={item.label} className={`gtc-nav__item${item.cta ? " gtc-nav__item--cta" : ""}`}>
        <a className={`gtc-nav__link${item.cta ? " gtc-nav__link--cta" : ""}`} href={item.href}>
          {item.label}
        </a>
      </li>
    );
  };

  return (
    <header className="gtc-header">
      <div className="container gtc-header__inner">
        <a href="#top" className="gtc-header__brand" aria-label="GoToCloud — inicio">
          <Logo variant="light" />
        </a>

        <nav className="gtc-nav" aria-label="Navegación principal">
          <ul className="gtc-nav__list">
            {PRIMARY_NAV.map(renderDesktopItem)}
          </ul>
        </nav>

        <div className="gtc-header__social">
          {SOCIAL_LINKS.map((s) => (
            <a key={s.icon} href={s.href} target="_blank" rel="noopener noreferrer" aria-label={s.label} className="gtc-header__social-link">
              <SocialIcon icon={s.icon} size={18} />
            </a>
          ))}
        </div>

        <button
          type="button"
          className="gtc-header__burger"
          aria-label={mobileOpen ? "Cerrar menú" : "Abrir menú"}
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen((v) => !v)}
        >
          {mobileOpen ? <CloseIcon size={24} /> : <MenuIcon size={24} />}
        </button>
      </div>

      {/* MOBILE DRAWER */}
      <div className={`gtc-mobile${mobileOpen ? " is-open" : ""}`} aria-hidden={!mobileOpen}>
        <nav className="gtc-mobile__nav" aria-label="Navegación móvil">
          <ul>
            {PRIMARY_NAV.map((item) =>
              item.children ? (
                <MobileGroup key={item.label} item={item} />
              ) : (
                <li key={item.label} className="gtc-mobile__item">
                  <a className={`gtc-mobile__link${item.cta ? " gtc-mobile__link--cta" : ""}`} href={item.href} onClick={() => setMobileOpen(false)}>
                    {item.label}
                  </a>
                </li>
              )
            )}
          </ul>

          <div className="gtc-mobile__social">
            {SOCIAL_LINKS.map((s) => (
              <a key={s.icon} href={s.href} target="_blank" rel="noopener noreferrer" aria-label={s.label}>
                <SocialIcon icon={s.icon} size={20} />
              </a>
            ))}
          </div>
        </nav>
      </div>
    </header>
  );
}

/** Item con sub-links en el drawer móvil */
function MobileGroup({ item }: { item: NavMenuItem }) {
  const [open, setOpen] = useState(false);
  return (
    <li className={`gtc-mobile__item gtc-mobile__item--group${open ? " is-open" : ""}`}>
      <button type="button" className="gtc-mobile__group-trigger" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        <span>{item.label}</span>
        <ChevronDownIcon size={14} />
      </button>
      {open && (
        <ul className="gtc-mobile__sublist">
          {item.children!.map((c) => (
            <li key={c.href}>
              <a className="gtc-mobile__sublink" href={c.href}>{c.label}</a>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}
