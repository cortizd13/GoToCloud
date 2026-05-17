import { useCallback, useEffect, useMemo, useState } from "react";
import { FiAlertCircle, FiDatabase, FiDownload, FiRefreshCw } from "react-icons/fi";
import type {
  DashboardBreakdownItem,
  DashboardHourlyPoint,
  DashboardSummary,
} from "../../domain/dashboard";
import { getDashboardSummary } from "../../infrastructure/api/dashboard.api";
import "./DashboardSection.css";

type DashboardState =
  | { status: "loading"; data: DashboardSummary | null; error: null }
  | { status: "ready"; data: DashboardSummary; error: null }
  | { status: "error"; data: DashboardSummary | null; error: string };

const emptySummary: DashboardSummary = {
  generatedAt: new Date().toISOString(),
  range: "today",
  overview: [
    {
      id: "volume",
      label: "Volumen total",
      value: "0",
      detail: "conversaciones hoy · vs ayer",
      trend: { value: "0%", direction: "flat" },
    },
    {
      id: "csat",
      label: "CSAT promedio",
      value: "N/D",
      detail: "de 5.0 · eventos Supabase",
      trend: { value: "N/D", direction: "flat" },
    },
    {
      id: "fcr",
      label: "First contact res.",
      value: "N/D",
      detail: "resuelto sin escalar",
      trend: { value: "N/D", direction: "flat" },
    },
    {
      id: "aht",
      label: "AHT promedio",
      value: "N/D",
      detail: "tiempo promedio de manejo",
      trend: { value: "N/D", direction: "flat" },
    },
  ],
  volumeByHour: Array.from({ length: 24 }, (_, hour) => ({
    hour: `${String(hour).padStart(2, "0")}:00`,
    conversations: 0,
    sentimentPositive: 0,
    sentimentNegative: 0,
  })),
  contactReasons: [],
  channels: [],
  recommendations: [],
  source: {
    sessions: 0,
    calls: 0,
    messages: 0,
    events: 0,
  },
};

function formatGeneratedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Sin sincronizar";
  }

  return new Intl.DateTimeFormat("es-CO", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function getMaxVolume(points: DashboardHourlyPoint[]): number {
  return Math.max(1, ...points.map((point) => point.conversations));
}

function downloadReport(summary: DashboardSummary) {
  const blob = new Blob([JSON.stringify(summary, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `gotocloud-dashboard-${new Date().toISOString().slice(0, 10)}.json`;
  link.click();
  URL.revokeObjectURL(url);
}

function BreakdownList({
  emptyLabel,
  items,
}: {
  emptyLabel: string;
  items: DashboardBreakdownItem[];
}) {
  if (!items.length) {
    return <p className="dashboard-empty">{emptyLabel}</p>;
  }

  return (
    <ul className="dashboard-breakdown">
      {items.map((item) => (
        <li className="dashboard-breakdown__item" key={item.label}>
          <div className="dashboard-breakdown__row">
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </div>
          <div className="dashboard-progress" aria-hidden="true">
            <span style={{ width: `${Math.min(100, item.percentage)}%` }} />
          </div>
          <small>{item.percentage}%</small>
        </li>
      ))}
    </ul>
  );
}

export function DashboardSection() {
  const [state, setState] = useState<DashboardState>({
    status: "loading",
    data: null,
    error: null,
  });

  const loadDashboard = useCallback((signal?: AbortSignal) => {
    setState((current) => ({
      status: "loading",
      data: current.data,
      error: null,
    }));

    getDashboardSummary(signal)
      .then((data) => setState({ status: "ready", data, error: null }))
      .catch((error: Error) => {
        if (signal?.aborted) {
          return;
        }

        setState((current) => ({
          status: "error",
          data: current.data,
          error: error.message,
        }));
      });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    getDashboardSummary(controller.signal)
      .then((data) => setState({ status: "ready", data, error: null }))
      .catch((error: Error) => {
        if (controller.signal.aborted) {
          return;
        }

        setState({
          status: "error",
          data: null,
          error: error.message,
        });
      });

    return () => controller.abort();
  }, []);

  const summary = state.data ?? emptySummary;
  const maxVolume = useMemo(
    () => getMaxVolume(summary.volumeByHour),
    [summary.volumeByHour],
  );
  const isLoading = state.status === "loading";

  return (
    <main className="dashboard-shell">
      <aside className="dashboard-sidebar" aria-label="Navegación dashboard">
        <a className="dashboard-sidebar__brand" href="/">
          GoToCloud
          <span>Contact Center IA</span>
        </a>
        <nav className="dashboard-sidebar__nav">
          <a className="is-active" href="/dashboard">Resumen</a>
          <a href="/dashboard#conversaciones">Conversaciones</a>
          <a href="/dashboard#canales">Canales</a>
          <a href="/dashboard#agente">Agente IA</a>
          <a href="/dashboard#reportes">Reportes</a>
        </nav>
        <div className="dashboard-sidebar__status">
          <FiDatabase aria-hidden="true" />
          <span>Supabase</span>
          <strong>{state.status === "error" ? "Revisar" : "Conectado"}</strong>
        </div>
      </aside>

      <section className="dashboard-main" aria-labelledby="dashboard-title">
        <header className="dashboard-header">
          <div>
            <p className="dashboard-kicker">Resumen ejecutivo</p>
            <h1 id="dashboard-title">Contact Center IA</h1>
            <p className="dashboard-subtitle">
              Actualizado desde Supabase · {formatGeneratedAt(summary.generatedAt)}
            </p>
          </div>

          <div className="dashboard-actions">
            <div className="dashboard-range" aria-label="Rango de fechas">
              <button className="is-active" type="button">Día</button>
              <button type="button">Semana</button>
              <button type="button">Mes</button>
            </div>
            <button
              className="dashboard-icon-button"
              disabled={isLoading}
              onClick={() => loadDashboard()}
              title="Actualizar"
              type="button"
            >
              <FiRefreshCw aria-hidden="true" />
              <span className="visually-hidden">Actualizar</span>
            </button>
            <button
              className="dashboard-icon-button dashboard-icon-button--primary"
              onClick={() => downloadReport(summary)}
              title="Exportar reporte"
              type="button"
            >
              <FiDownload aria-hidden="true" />
              <span className="visually-hidden">Exportar reporte</span>
            </button>
          </div>
        </header>

        {state.status === "error" && (
          <div className="dashboard-alert" role="alert">
            <FiAlertCircle aria-hidden="true" />
            <span>{state.error}</span>
          </div>
        )}

        <section className="dashboard-metrics" aria-label="Indicadores principales">
          {summary.overview.map((metric) => (
            <article
              className={`dashboard-metric ${isLoading ? "is-loading" : ""}`}
              key={metric.id}
            >
              <span>{metric.label}</span>
              <strong>{metric.value}</strong>
              <div>
                <small className={`trend trend--${metric.trend.direction}`}>
                  {metric.trend.value}
                </small>
                <small>{metric.detail}</small>
              </div>
            </article>
          ))}
        </section>

        <section className="dashboard-grid">
          <article className="dashboard-panel dashboard-panel--wide" id="conversaciones">
            <div className="dashboard-panel__header">
              <div>
                <h2>Volumen y sentimiento</h2>
                <p>Conversaciones por hora · sentimiento registrado</p>
              </div>
              <div className="dashboard-legend">
                <span><i className="legend-volume" />Volumen</span>
                <span><i className="legend-positive" />Sentimiento +</span>
                <span><i className="legend-negative" />Sentimiento -</span>
              </div>
            </div>
            <div className="dashboard-chart" aria-label="Conversaciones por hora">
              {summary.volumeByHour.map((point) => {
                const height = Math.max(
                  6,
                  Math.round((point.conversations / maxVolume) * 100),
                );

                return (
                  <div className="dashboard-chart__bar" key={point.hour}>
                    <span
                      className="dashboard-chart__positive"
                      style={{ height: `${point.sentimentPositive * 6}px` }}
                    />
                    <span
                      className="dashboard-chart__negative"
                      style={{ height: `${point.sentimentNegative * 6}px` }}
                    />
                    <strong style={{ height: `${height}%` }} />
                    <small>{point.hour.slice(0, 2)}</small>
                  </div>
                );
              })}
            </div>
          </article>

          <article className="dashboard-panel">
            <div className="dashboard-panel__header">
              <div>
                <h2>Motivos de contacto</h2>
                <p>Top 6 · datos del día</p>
              </div>
            </div>
            <BreakdownList
              emptyLabel="Sin motivos registrados en Supabase para hoy."
              items={summary.contactReasons}
            />
          </article>

          <article className="dashboard-panel" id="canales">
            <div className="dashboard-panel__header">
              <div>
                <h2>Mix por canal</h2>
                <p>Voz · WhatsApp · Chat · SMS</p>
              </div>
            </div>
            <BreakdownList
              emptyLabel="Sin conversaciones por canal para hoy."
              items={summary.channels}
            />
          </article>

          <article className="dashboard-panel dashboard-panel--wide" id="agente">
            <div className="dashboard-panel__header">
              <div>
                <h2>Recomendaciones del agente IA</h2>
                <p>Generadas con patrones actuales de Supabase</p>
              </div>
              <span className="dashboard-source">
                {summary.source.sessions} sesiones · {summary.source.calls} llamadas ·{" "}
                {summary.source.messages} mensajes
              </span>
            </div>
            <ol className="dashboard-recommendations">
              {summary.recommendations.map((recommendation, index) => (
                <li key={recommendation.id}>
                  <span>{index + 1}</span>
                  <p>{recommendation.title}</p>
                  <strong data-impact={recommendation.impact}>
                    impacto {recommendation.impact}
                  </strong>
                </li>
              ))}
            </ol>
          </article>
        </section>
      </section>
    </main>
  );
}
