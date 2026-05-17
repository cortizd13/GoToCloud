# Web Voice Chat — Camila desde el Navegador — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar el link `tel:` del botón "Llamar" por un `VoiceCallWidget` que conecta al endpoint `/web-stream` del backend via WebSocket, captura audio del micrófono con AudioWorklet y reproduce la voz de Camila en tiempo real.

**Architecture:** `VoiceSession` (clase pura TypeScript) gestiona el WebSocket, el pipeline AudioWorklet de captura (48kHz→16kHz PCM16) y la cola de playback (PCM16 24kHz). `VoiceCallWidget` es el componente React que usa `VoiceSession` y muestra estado + transcript. `ContactCenterButton` lo monta igual que monta `ChatbotWidget` cuando se abre "Correo".

**Tech Stack:** React 19, TypeScript strict, Vite 8, Web Audio API (AudioWorklet), WebSocket binary frames, `react-icons/md`.

**Working directory para todos los comandos:** `gotocloud-frontend/`

---

## Mapa de archivos

| Acción | Archivo |
|---|---|
| Crear | `src/domain/voice.ts` |
| Crear | `src/shared/audio/pcm-processor.worklet.ts` |
| Crear | `src/infrastructure/api/voice.api.ts` |
| Crear | `src/presentation/layout/VoiceCallWidget.css` |
| Crear | `src/presentation/layout/VoiceCallWidget.tsx` |
| Modificar | `src/presentation/layout/ContactCenterMenu.tsx` |
| Modificar | `src/presentation/layout/ContactCenterButton.tsx` |

---

## Task 1: Domain types

**Files:**
- Create: `src/domain/voice.ts`

- [ ] **Step 1.1 — Crear el archivo de tipos**

```typescript
// src/domain/voice.ts
export type CallStatus = 'connecting' | 'listening' | 'speaking' | 'ended' | 'error';

export type TranscriptEntry = {
  id: string;
  role: 'user' | 'model';
  text: string;
};
```

- [ ] **Step 1.2 — Verificar que TypeScript compila**

```bash
npm run build
```

Resultado esperado: compilación exitosa (puede advertir sobre archivos aún no creados — se resuelve en tasks siguientes; si hay errores de tipo en archivos _existentes_, investiga antes de continuar).

---

## Task 2: AudioWorklet processor

**Files:**
- Create: `src/shared/audio/pcm-processor.worklet.ts`

El worklet corre en `AudioWorkletGlobalScope` — un hilo separado con sus propios globales (`sampleRate`, `AudioWorkletProcessor`, `registerProcessor`). TypeScript no verifica este scope, por eso va `// @ts-nocheck`.

- [ ] **Step 2.1 — Crear el procesador**

```typescript
// src/shared/audio/pcm-processor.worklet.ts
// @ts-nocheck
// Runs in AudioWorkletGlobalScope — no DOM, no module imports allowed.

class PcmProcessor extends AudioWorkletProcessor {
  // Phase accumulator for fractional downsampling.
  // At 48kHz → 16kHz: ratio = 3.0, advance phase by 3 per output sample.
  // At 44100Hz → 16kHz: ratio = 2.75625, handled correctly by float math.
  _phase = 0;

  process(inputs) {
    const channel = inputs[0]?.[0];
    if (!channel || channel.length === 0) return true;

    const ratio = sampleRate / 16000;
    const result = [];

    while (this._phase < channel.length) {
      result.push(channel[Math.floor(this._phase)]);
      this._phase += ratio;
    }
    this._phase -= channel.length; // carry fractional offset to next frame

    if (result.length === 0) return true;

    const int16 = new Int16Array(result.length);
    for (let i = 0; i < result.length; i++) {
      const s = Math.max(-1, Math.min(1, result[i]));
      int16[i] = Math.round(s < 0 ? s * 32768 : s * 32767);
    }

    // Transfer ownership of the buffer — zero-copy to main thread
    this.port.postMessage(int16.buffer, [int16.buffer]);
    return true;
  }
}

registerProcessor('pcm-processor', PcmProcessor);
```

- [ ] **Step 2.2 — Verificar build**

```bash
npm run build
```

Resultado esperado: `src/shared/audio/pcm-processor.worklet.ts` procesado sin errores (el `// @ts-nocheck` suprime advertencias del scope desconocido).

- [ ] **Step 2.3 — Commit**

```bash
git add src/domain/voice.ts src/shared/audio/pcm-processor.worklet.ts
git commit -m "feat(voice): domain types + AudioWorklet PCM processor"
```

---

## Task 3: Voice API — WebSocket + audio pipeline

**Files:**
- Create: `src/infrastructure/api/voice.api.ts`

Esta clase encapsula todo lo que no es React: WebSocket, captura de micrófono, playback. El componente solo interactúa con ella a través de callbacks y `hangUp()`.

- [ ] **Step 3.1 — Crear `voice.api.ts`**

```typescript
// src/infrastructure/api/voice.api.ts
import type { TranscriptEntry } from '../../domain/voice';
import processorUrl from '../../shared/audio/pcm-processor.worklet.ts?url';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

function getWsUrl(): string {
  // http://host → ws://host/web-stream
  // https://host → wss://host/web-stream
  return API_BASE_URL.replace(/^http/, 'ws') + '/web-stream';
}

export type VoiceStatusValue = 'connected' | 'listening' | 'speaking' | 'ended';

export type VoiceEvent =
  | { type: 'status'; value: VoiceStatusValue }
  | { type: 'transcript'; role: TranscriptEntry['role']; text: string }
  | { type: 'error'; message: string };

export type VoiceSessionCallbacks = {
  onEvent: (event: VoiceEvent) => void;
  onClose: () => void;
};

export class VoiceSession {
  private readonly ws: WebSocket;
  private audioContext: AudioContext | null = null;
  private workletNode: AudioWorkletNode | null = null;
  private mediaStream: MediaStream | null = null;
  private nextPlayTime = 0;

  constructor(private readonly callbacks: VoiceSessionCallbacks) {
    this.ws = new WebSocket(getWsUrl());
    this.ws.binaryType = 'arraybuffer';

    this.ws.onmessage = (ev) => {
      if (ev.data instanceof ArrayBuffer) {
        this._playChunk(ev.data);
      } else {
        this._handleTextFrame(ev.data as string);
      }
    };

    this.ws.onerror = () => {
      callbacks.onEvent({ type: 'error', message: 'No se pudo conectar con Camila' });
    };

    this.ws.onclose = () => callbacks.onClose();
  }

  private _handleTextFrame(raw: string): void {
    let msg: Record<string, unknown>;
    try {
      msg = JSON.parse(raw) as Record<string, unknown>;
    } catch {
      return;
    }

    if (msg.type === 'status') {
      this.callbacks.onEvent({ type: 'status', value: msg.value as VoiceStatusValue });
    } else if (msg.type === 'transcript') {
      this.callbacks.onEvent({
        type: 'transcript',
        role: msg.role as TranscriptEntry['role'],
        text: msg.text as string,
      });
    } else if (msg.type === 'error') {
      this.callbacks.onEvent({ type: 'error', message: msg.message as string });
    }
    // 'tool' events are ignored — internal Gemini tool calls
  }

  async startCapture(): Promise<void> {
    this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    this.audioContext = new AudioContext();
    await this.audioContext.audioWorklet.addModule(processorUrl);

    const source = this.audioContext.createMediaStreamSource(this.mediaStream);
    this.workletNode = new AudioWorkletNode(this.audioContext, 'pcm-processor');

    this.workletNode.port.onmessage = (ev: MessageEvent<ArrayBuffer>) => {
      if (this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(ev.data);
      }
    };

    // Connect source → worklet (NOT to destination — avoids mic feedback)
    source.connect(this.workletNode);
  }

  private _playChunk(buffer: ArrayBuffer): void {
    if (!this.audioContext) return;

    const int16 = new Int16Array(buffer);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
      float32[i] = int16[i] / 32767;
    }

    const audioBuffer = this.audioContext.createBuffer(1, float32.length, 24000);
    audioBuffer.getChannelData(0).set(float32);

    const source = this.audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(this.audioContext.destination);

    const now = this.audioContext.currentTime;
    // If queue fell behind (tab in background), reset 50ms ahead
    if (this.nextPlayTime < now) {
      this.nextPlayTime = now + 0.05;
    }
    source.start(this.nextPlayTime);
    this.nextPlayTime += audioBuffer.duration;
  }

  hangUp(): void {
    if (this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'stop' }));
      this.ws.close();
    }
    this.workletNode?.disconnect();
    this.mediaStream?.getTracks().forEach((t) => t.stop());
    this.audioContext?.close().catch(() => undefined);
  }
}
```

- [ ] **Step 3.2 — Verificar build**

```bash
npm run build
```

Resultado esperado: sin errores de TypeScript. Si aparece un error sobre `processorUrl` no siendo un módulo reconocido, verificá que el archivo `.worklet.ts` existe en el path correcto.

- [ ] **Step 3.3 — Commit**

```bash
git add src/infrastructure/api/voice.api.ts
git commit -m "feat(voice): VoiceSession — WebSocket + AudioWorklet capture + PCM playback"
```

---

## Task 4: VoiceCallWidget — CSS

**Files:**
- Create: `src/presentation/layout/VoiceCallWidget.css`

Reutiliza las clases del `ChatbotWidget` (`.chatbot-widget`, `.chatbot-widget__header`, `.chatbot-widget__agent`, `.chatbot-widget__avatar`, `.chatbot-widget__message--assistant`, `.chatbot-widget__message--user`) para la estructura de la tarjeta. Solo agrega clases para las partes nuevas.

- [ ] **Step 4.1 — Crear el CSS**

```css
/* src/presentation/layout/VoiceCallWidget.css */

.voice-call-widget__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  overflow-y: auto;
  background:
    linear-gradient(180deg, rgba(247, 249, 252, 0.92), rgba(255, 255, 255, 0.94)),
    var(--gtc-gray-50);
}

/* ── Status badge ──────────────────────────────────── */
.voice-call-widget__status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-full);
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
  align-self: center;
  margin-top: auto;
}

.voice-call-widget__status--connecting {
  color: var(--gtc-gray-400);
  background: var(--gtc-gray-100);
}

.voice-call-widget__status--listening {
  color: #16a34a;
  background: #dcfce7;
}

.voice-call-widget__status--speaking {
  color: var(--gtc-blue-500);
  background: #dbeafe;
}

.voice-call-widget__status--ended {
  color: var(--gtc-gray-500);
  background: var(--gtc-gray-100);
}

.voice-call-widget__status--error {
  color: #dc2626;
  background: #fee2e2;
}

@keyframes voice-pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.55; }
}

.voice-call-widget__status--listening,
.voice-call-widget__status--speaking {
  animation: voice-pulse 1.5s ease-in-out infinite;
}

/* ── Live badge (header) ───────────────────────────── */
.voice-call-widget__live-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  background: #dc2626;
  color: #fff;
  font-size: 10px;
  font-weight: var(--fw-semibold);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  flex-shrink: 0;
}

.voice-call-widget__live-badge::before {
  content: '';
  display: block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #fff;
  animation: voice-pulse 1s ease-in-out infinite;
}

/* ── Footer / Colgar ───────────────────────────────── */
.voice-call-widget__footer {
  display: flex;
  justify-content: center;
  padding: var(--space-3);
  border-top: 1px solid var(--color-border);
  background: var(--gtc-white);
}

.voice-call-widget__hangup {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-6);
  border-radius: var(--radius-full);
  color: #fff;
  background: #dc2626;
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
  transition:
    background var(--dur-base) var(--ease),
    transform var(--dur-base) var(--ease);
}

.voice-call-widget__hangup:hover {
  background: #b91c1c;
  transform: scale(1.03);
}

.voice-call-widget__hangup:active {
  transform: scale(0.98);
}
```

---

## Task 5: VoiceCallWidget — componente React

**Files:**
- Create: `src/presentation/layout/VoiceCallWidget.tsx`

- [ ] **Step 5.1 — Crear el componente**

```tsx
// src/presentation/layout/VoiceCallWidget.tsx
import { useEffect, useRef, useState } from 'react';
import { MdOutlineSmartToy, MdPhoneDisabled } from 'react-icons/md';
import { VoiceSession } from '../../infrastructure/api/voice.api';
import type { VoiceEvent } from '../../infrastructure/api/voice.api';
import type { CallStatus, TranscriptEntry } from '../../domain/voice';
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
    const session = new VoiceSession({
      onEvent: (ev: VoiceEvent) => {
        if (ev.type === 'status') {
          if (ev.value === 'connected' || ev.value === 'listening') {
            setStatus('listening');
          } else if (ev.value === 'speaking') {
            setStatus('speaking');
          } else if (ev.value === 'ended') {
            setStatus('ended');
          }
        } else if (ev.type === 'transcript') {
          setTranscript((prev) => [...prev, makeEntry(ev.role, ev.text)]);
        } else if (ev.type === 'error') {
          setErrorMsg(ev.message);
          setStatus('error');
        }
      },
      onClose: () => {
        setStatus((prev) => (prev === 'error' ? prev : 'ended'));
      },
    });

    sessionRef.current = session;

    session.startCapture().catch((err: unknown) => {
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
            <MdOutlineSmartToy size={22} />
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

      <div className="voice-call-widget__body" aria-live="polite">
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
```

- [ ] **Step 5.2 — Verificar build**

```bash
npm run build
```

Resultado esperado: sin errores. Si `noUnusedLocals` se queja de algo, revisá los imports.

- [ ] **Step 5.3 — Commit**

```bash
git add src/presentation/layout/VoiceCallWidget.css src/presentation/layout/VoiceCallWidget.tsx
git commit -m "feat(voice): VoiceCallWidget — transcript + status + colgar"
```

---

## Task 6: Modificar ContactCenterMenu

**Files:**
- Modify: `src/presentation/layout/ContactCenterMenu.tsx`

- [ ] **Step 6.1 — Reemplazar el archivo completo**

El cambio: agregar `onOpenCall` a las props, eliminar "Llamar" del array de links (que solo renderizaba `<a>` tags), agregar "Llamar" como `<button>` junto a "Correo", y eliminar el import de `CONTACT_INFO` que ya no se usa.

```tsx
// src/presentation/layout/ContactCenterMenu.tsx
import { getWhatsAppUrl } from "../../application/whatsapp";
import { MailIcon, PhoneIcon, SocialIcon } from "../../shared/ui/icons";
import "./ContactCenterButton.css";

type ContactCenterMenuProps = {
  id: string;
  onOpenChat: () => void;
  onOpenCall: () => void;
  onSelect: () => void;
};

function ContactCenterMenu({ id, onOpenChat, onOpenCall, onSelect }: ContactCenterMenuProps) {
  return (
    <div className="contact-center-menu" id={id} role="menu" aria-label="Opciones de contacto">
      <a
        className="contact-center-menu__item"
        href={getWhatsAppUrl({
          intent: "Contactar al equipo comercial de GoToCloud",
          detail: "Quiero recibir asesoría sobre soluciones cloud.",
          source: "gotocloud.com.co",
        })}
        target="_blank"
        rel="noopener noreferrer"
        aria-label="WhatsApp"
        title="WhatsApp"
        role="menuitem"
        onClick={onSelect}
      >
        <span className="contact-center-menu__label">WhatsApp</span>
        <SocialIcon icon="whatsapp" size={24} />
      </a>

      <button
        type="button"
        className="contact-center-menu__item"
        aria-label="Llamar a Camila"
        title="Llamar"
        role="menuitem"
        onClick={() => {
          onOpenCall();
          onSelect();
        }}
      >
        <span className="contact-center-menu__label">Llamar</span>
        <PhoneIcon size={24} />
      </button>

      <button
        type="button"
        className="contact-center-menu__item"
        aria-label="Correo"
        title="Correo"
        role="menuitem"
        onClick={() => {
          onOpenChat();
          onSelect();
        }}
      >
        <span className="contact-center-menu__label">Correo</span>
        <MailIcon size={24} />
      </button>
    </div>
  );
}

export default ContactCenterMenu;
```

**Nota:** `CONTACT_INFO` queda importado pero no usado — lo eliminamos en el siguiente paso si TypeScript lo señala con `noUnusedLocals`. Verificá el build y removelo del import si aparece el error.

- [ ] **Step 6.2 — Verificar build**

```bash
npm run build
```

Resultado esperado: sin errores. El import de `CONTACT_INFO` fue eliminado en el paso anterior para cumplir con `noUnusedLocals: true`.

- [ ] **Step 6.3 — Commit**

```bash
git add src/presentation/layout/ContactCenterMenu.tsx
git commit -m "feat(voice): ContactCenterMenu — Llamar abre voice widget en lugar de tel:"
```

---

## Task 7: Modificar ContactCenterButton

**Files:**
- Modify: `src/presentation/layout/ContactCenterButton.tsx`

- [ ] **Step 7.1 — Reemplazar el archivo completo**

```tsx
// src/presentation/layout/ContactCenterButton.tsx
import { useEffect, useId, useRef, useState } from "react";
import { MdSupportAgent } from "react-icons/md";
import { CloseIcon } from "../../shared/ui/icons";
import "./ContactCenterButton.css";
import ChatbotWidget from "./ChatbotWidget";
import ContactCenterMenu from "./ContactCenterMenu";
import VoiceCallWidget from "./VoiceCallWidget";

function ContactCenterButton() {
  const [open, setOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [callOpen, setCallOpen] = useState(false);
  const menuId = useId();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    const closeWithEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };

    const closeWhenClickingOutside = (event: PointerEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    document.addEventListener("keydown", closeWithEscape);
    document.addEventListener("pointerdown", closeWhenClickingOutside);

    return () => {
      document.removeEventListener("keydown", closeWithEscape);
      document.removeEventListener("pointerdown", closeWhenClickingOutside);
    };
  }, [open]);

  return (
    <div className={`contact-center${open ? " is-open" : ""}`} ref={containerRef}>
      {chatOpen && <ChatbotWidget onClose={() => setChatOpen(false)} />}
      {callOpen && <VoiceCallWidget onClose={() => setCallOpen(false)} />}

      {open && (
        <ContactCenterMenu
          id={menuId}
          onOpenChat={() => {
            setCallOpen(false);
            setOpen(false);
            setChatOpen(true);
          }}
          onOpenCall={() => {
            setChatOpen(false);
            setOpen(false);
            setCallOpen(true);
          }}
          onSelect={() => setOpen(false)}
        />
      )}

      <button
        type="button"
        className="contact-center-button"
        aria-controls={open ? menuId : undefined}
        aria-expanded={open}
        aria-label={open ? "Cerrar centro de contacto" : "Abrir centro de contacto"}
        onClick={() => {
          setChatOpen(false);
          setCallOpen(false);
          setOpen((isOpen) => !isOpen);
        }}
      >
        {open ? <CloseIcon size={30} /> : <MdSupportAgent size={32} />}
      </button>
    </div>
  );
}

export default ContactCenterButton;
```

- [ ] **Step 7.2 — Build final completo**

```bash
npm run build
```

Resultado esperado:
```
✓ built in X.XXs
```
Sin errores de TypeScript ni de Vite.

- [ ] **Step 7.3 — Commit**

```bash
git add src/presentation/layout/ContactCenterButton.tsx
git commit -m "feat(voice): ContactCenterButton — monta VoiceCallWidget al hacer clic en Llamar"
```

---

## Task 8: Smoke test end-to-end

Este task no tiene código que escribir — es verificación manual que el feature funciona completo.

**Prerequisitos:**
- Backend corriendo: `cd gotocloudgemini && venv\Scripts\python -m uvicorn backend.main:app --reload`
- Frontend corriendo: `cd gotocloud-frontend && npm run dev`
- `backend/.env` tiene `GEMINI_API_KEY` configurado

- [ ] **Step 8.1 — Abrir el frontend**

Ir a `http://localhost:5173` en el navegador.

- [ ] **Step 8.2 — Abrir el menú de contacto**

Hacer clic en el botón flotante naranja (abajo a la derecha). Debe aparecer el menú con tres opciones: WhatsApp, Llamar, Correo.

- [ ] **Step 8.3 — Iniciar llamada**

Hacer clic en "Llamar". El browser debe pedir permiso de micrófono. Conceder el permiso.

**Resultado esperado:** Aparece el `VoiceCallWidget` con:
- Header "Camila / Llamada de voz"
- Badge verde "Escuchando…" (pulsando)
- Transcript vacío

- [ ] **Step 8.4 — Verificar que Camila saluda**

Esperar ~2-3 segundos. Camila debe saludar y pedir el nombre del cliente. El saludo aparece en el transcript como burbuja de "Camila" y se escucha por los speakers.

**Si no hay audio:** Verificar en la consola del browser (DevTools → Console) que no haya errores de WebSocket. Verificar que el backend esté corriendo en `localhost:8000`.

- [ ] **Step 8.5 — Conversación breve**

Hablar con Camila (ej: "Hola, me llamo Juan"). Verificar que:
- Tu voz aparece en el transcript como burbuja del usuario
- Camila responde por audio y en el transcript

- [ ] **Step 8.6 — Colgar**

Hacer clic en "Colgar". El widget debe cerrarse. La luz del micrófono del sistema operativo debe apagarse.

- [ ] **Step 8.7 — Verificar en Supabase (opcional)**

Si hay Supabase configurado, verificar en el dashboard de Supabase que:
- Tabla `clientes`: aparece el registro del cliente si Camila lo registró
- Tabla `llamadas`: aparece la llamada si llegó al cierre

- [ ] **Step 8.8 — Lint check**

```bash
npm run lint
```

Resultado esperado: sin errores propios del proyecto.

- [ ] **Step 8.9 — Commit final**

```bash
git add -A
git commit -m "feat(voice): web voice chat con Camila — end-to-end funcional"
```

---

## Troubleshooting

| Síntoma | Causa probable | Fix |
|---|---|---|
| `WebSocket connection failed` | Backend no está corriendo o URL incorrecta | Verificar `VITE_API_BASE_URL` en `.env` y que `uvicorn` esté activo |
| No llega audio de Camila | `audioContext` suspendido (política autoplay) | El `AudioContext` se crea en `startCapture()` que es llamado desde un handler de usuario — ya está resuelto |
| Micrófono no se apaga al colgar | `hangUp()` no llegó a ejecutarse | Verificar que el `useEffect` cleanup llame `session.hangUp()` |
| `'pcm-processor' is not defined` | Worklet no cargó | Verificar path del import `?url` y que Vite pueda resolver el archivo |
| TypeScript error en worklet | Scope de AudioWorklet | El archivo debe tener `// @ts-nocheck` como primera línea |
| `noUnusedLocals` error en Menu | Import sobrante | Verificar que no haya imports sin usar en el archivo modificado |
