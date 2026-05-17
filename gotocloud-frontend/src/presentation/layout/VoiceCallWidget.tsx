// src/presentation/layout/VoiceCallWidget.tsx
import { useEffect, useRef, useState } from 'react';
import {  MdPhoneDisabled } from 'react-icons/md';
import { VoiceSession } from '../../infrastructure/api/voice.api';
import type { VoiceEvent } from '../../infrastructure/api/voice.api';
import type { CallStatus, TranscriptEntry } from '../../domain/voice';
import CamilaImage from '../../shared/img/camila.jpeg';
import './VoiceCallWidget.css';

type Props = { onClose: () => void };

const STATUS_LABELS: Record<CallStatus, string> = {
  connecting: 'Conectando…',
  listening:  'Escuchando…',
  speaking:   'Camila está hablando…',
  ended:      'Llamada finalizada',
  error:      '',
};

function makeEntry(role: TranscriptEntry['role'], text: string): TranscriptEntry {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    text,
  };
}

export default function VoiceCallWidget({ onClose }: Props) {
  const [status, setStatus] = useState<CallStatus>('connecting');
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [errorMsg, setErrorMsg] = useState('');
  const sessionRef = useRef<VoiceSession | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll cuando llega nuevo texto o cambia el status
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [transcript, status]);

  useEffect(() => {
    let active = true;

    const session = new VoiceSession({
      onEvent: (ev: VoiceEvent) => {
        if (!active) return;
        if (ev.type === 'status') {
          if (ev.value === 'connected' || ev.value === 'listening') {
            setStatus('listening');
          } else if (ev.value === 'speaking') {
            setStatus('speaking');
          } else if (ev.value === 'ended') {
            setStatus('ended');
          }
        } else if (ev.type === 'transcript') {
          // Streaming: append to last bubble if same role, else create new one
          setTranscript((prev) => {
            const last = prev[prev.length - 1];
            if (last && last.role === ev.role) {
              return [...prev.slice(0, -1), { ...last, text: last.text + ev.text }];
            }
            return [...prev, makeEntry(ev.role, ev.text)];
          });
        } else if (ev.type === 'error') {
          setErrorMsg(ev.message);
          setStatus('error');
        }
      },
      onClose: () => {
        if (!active) return;
        setStatus((prev) => (prev === 'error' ? prev : 'ended'));
      },
    });

    sessionRef.current = session;

    session.startCapture().catch((err: unknown) => {
      if (!active) return;
      const isPermissionDenied =
        err instanceof DOMException && err.name === 'NotAllowedError';
      setErrorMsg(
        isPermissionDenied
          ? 'Necesitamos acceso al micrófono para la llamada'
          : 'No se pudo iniciar el micrófono',
      );
      setStatus('error');
    });

    return () => {
      active = false;
      session.hangUp();
    };
  }, []);

  function handleHangUp() {
    sessionRef.current?.hangUp();
    onClose();
  }

  const isLive = status === 'listening' || status === 'speaking';

  return (
    <section className="chatbot-widget" aria-label="Llamada de voz con Camila">
      <header className="chatbot-widget__header">
        <div className="chatbot-widget__agent">
          <span className="chatbot-widget__avatar">
            <img className="chatbot-widget__img" src={CamilaImage} alt="Icono Camila Bot" />
          </span>
          <div>
            <strong>Camila</strong>
            <span>Llamada de voz</span>
          </div>
        </div>
        {isLive && (
          <span className="voice-call-widget__live-badge" aria-label="En vivo">
            EN VIVO
          </span>
        )}
      </header>

      <div className="voice-call-widget__body">
        {transcript.map((entry) => (
          <div
            key={entry.id}
            className={`chatbot-widget__message chatbot-widget__message--${
              entry.role === 'model' ? 'assistant' : 'user'
            }`}
          >
            {entry.text}
          </div>
        ))}

        <div
          aria-live="polite"
          aria-atomic="true"
          className={`voice-call-widget__status voice-call-widget__status--${status}`}
        >
          {status === 'error' ? errorMsg : STATUS_LABELS[status]}
        </div>

        <div ref={bottomRef} />
      </div>

      <div className="voice-call-widget__footer">
        <button
          type="button"
          className="voice-call-widget__hangup"
          aria-label="Colgar llamada"
          onClick={handleHangUp}
        >
          <MdPhoneDisabled size={20} />
          Colgar
        </button>
      </div>
    </section>
  );
}
