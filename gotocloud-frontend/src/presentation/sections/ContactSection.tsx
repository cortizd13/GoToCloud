import { getContactSectionViewModel } from "../../application/contactSection";
import { MailIcon, MapPinIcon, PhoneIcon } from "../../shared/ui/icons";
import "./ContactSection.css";

export function ContactSection() {
  const vm = getContactSectionViewModel();

  return (
    <section className="gtc-contact" id="contacto">
      {/* HERO */}
      <div className="gtc-contact__hero">
        <div className="gtc-contact__bg-aura" aria-hidden="true" />
        <div className="container">
          <h1 className="gtc-contact__title">{vm.hero.title}</h1>
          <p className="gtc-contact__lead">
            Estamos listos para ayudarle a implementar estos escenarios de{" "}
            <strong>Azure y Microsoft</strong>, impulsando la transformación de
            su negocio.
            <br />
            <strong>Contáctenos</strong> para descubrir cómo podemos trabajar
            juntos en su proyecto de transformación digital y alcanzar el éxito.
          </p>
          <p className="gtc-contact__cta-label">Contáctenos:</p>
          <a className="gtc-contact__cta" >
            <MailIcon size={18} />
            <span>{vm.hero.email}</span>
          </a>
        </div>
      </div>

      {/* REGIONS */}
      <div className="gtc-regions">
        <div className="container">
          <h2 className="gtc-regions__title">{vm.regions.title}</h2>
          <div className="gtc-regions__divider" aria-hidden="true" />

          <ul className="gtc-regions__grid">
            {vm.regions.items.map((r) => (
              <li key={r.code} className="gtc-region">
                <div className="gtc-region__flag">
                  <img src={r.flag} alt={`Bandera de ${r.name}`} loading="lazy" />
                </div>
                <p className="gtc-region__name">
                  {r.name}
                  {r.tag && (
                    <span className="gtc-region__tag"> ({r.tag})</span>
                  )}
                </p>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* CONTACT INFO */}
      <div className="gtc-info">
        <div className="container">
          <h2 className="gtc-info__title">{vm.contact.title}</h2>
          <div className="gtc-info__divider" aria-hidden="true" />

          <div className="gtc-info__grid">
            <article className="gtc-info-card">
              <div className="gtc-info-card__icon">
                <PhoneIcon size={26} />
              </div>
              <h3 className="gtc-info-card__title">Teléfono de contacto</h3>
              <a
                className="gtc-info-card__text"
                href={vm.contact.info.phoneHref}
              >
                {vm.contact.info.phone}
              </a>
            </article>

            <article className="gtc-info-card">
              <div className="gtc-info-card__icon">
                <MapPinIcon size={26} />
              </div>
              <h3 className="gtc-info-card__title">Dirección</h3>
              <p className="gtc-info-card__text">{vm.contact.info.address}</p>
            </article>

            <article className="gtc-info-card">
              <div className="gtc-info-card__icon">
                <MailIcon size={26} />
              </div>
              <h3 className="gtc-info-card__title">Correo Electrónico</h3>
              <div className="gtc-info-card__emails">
                {vm.contact.info.emails.map((e) => (
                  <a key={e} href={`mailto:${e}`} className="gtc-info-card__email">
                    {e}
                  </a>
                ))}
              </div>
            </article>
          </div>
        </div>
      </div>
    </section>
  );
}
