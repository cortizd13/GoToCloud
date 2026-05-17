# Spec: Web Voice Chat — Camila desde el navegador

**Fecha:** 2026-05-17  
**Estado:** Aprobado por el usuario  
**Alcance:** Solo voice chat. Dashboard y WhatsApp son fases posteriores.

---

## 1. Contexto

GoToCloud tiene un monorepo con dos sub-proyectos:

- `gotocloud-frontend/` — React 19 + TypeScript + Vite. Página de contacto estática con un contact center button (menú flotante con WhatsApp, Llamar, Correo/Chat).
- `gotocloudgemini/` — Python 3.12 + FastAPI. Agente de voz "Camila" con Gemini Live API.

El backend ya tiene el endpoint `/web-stream` (WebSocket) listo para recibir audio PCM16 16kHz del browser y devolver PCM16 24kHz + eventos JSON. El frontend todavía no lo usa.

**Objetivo:** Conectar el botón "Llamar" del contact center al endpoint `/web-stream` para que el visitante hable con Camila directamente desde el navegador.

---

## 2. Qué cambia

### Frontend — archivos nuevos

| Archivo | Responsabilidad |
|---|---|
| `src/shared/audio/pcm-processor.worklet.ts` | AudioWorkletProcessor: captura mic, downsample 48→16kHz, convierte a Int16 |
| `src/infrastructure/api/voice.api.ts` | Abre WebSocket, gestiona pipeline de audio (captura + playback), expone interfaz simple |
| `src/presentation/layout/VoiceCallWidget.tsx` | Componente React: estado de la llamada, transcript, botón colgar |
| `src/presentation/layout/VoiceCallWidget.css` | Estilos del widget (misma tarjeta que ChatbotWidget) |

### Frontend — archivos modificados

| Archivo | Cambio |
|---|---|
| `src/presentation/layout/ContactCenterMenu.tsx` | "Llamar" pasa de `<a href="tel:...">` a `<button>` que llama `onOpenCall` |
| `src/presentation/layout/ContactCenterButton.tsx` | Agrega estado `callOpen`, renderiza `VoiceCallWidget`, pasa `onOpenCall` al menú |

### Backend — sin cambios

`/web-stream` ya está implementado y funcional. Los tools de Gemini (`registrar_datos_cliente`, `registrar_resumen_llamada`) ya persisten en Supabase.

---

## 3. Protocolo WebSocket `/web-stream`

```
Browser → Server : frames BINARIOS — PCM16 LE 16kHz (captura de micrófono)
                   frame TEXTO JSON {"type": "stop"} — al colgar

Server → Browser : frames BINARIOS — PCM16 LE 24kHz (audio de Gemini)
                   frames TEXTO JSON:
                     {"type": "status",     "value": "connected|listening|speaking|ended"}
                     {"type": "transcript", "role": "user|model", "text": "..."}
                     {"type": "tool",       "name": "...", "result": {...}}
                     {"type": "error",      "message": "..."}
```

URL: derivada de `VITE_API_BASE_URL` reemplazando `http://` → `ws://` y `https://` → `wss://`.

---

## 4. Audio pipeline

### 4.1 Captura (Mic → Gemini)

```
getUserMedia({ audio: true })
  → MediaStreamSourceNode (AudioContext nativo del browser, típicamente 48kHz)
  → AudioWorkletNode ("pcm-processor")
      • Recibe 128 muestras Float32 @ 48kHz por frame (2.7ms)
      • Downsample 3:1 → Float32 @ 16kHz
        (descarte simple — suficiente para voz <8kHz, sin filtro anti-aliasing)
      • Float32 → Int16 (× 32767, clamp a [-32768, 32767])
      • postMessage(Int16Array) → main thread
  → WebSocket.send(int16Array.buffer)  [binary frame]
```

El worklet corre en un hilo de audio dedicado con prioridad real-time. Latencia de captura: ~10–15ms (vs ~85ms con ScriptProcessorNode).

### 4.2 Playback (Gemini → Speaker)

```
WebSocket binary frame (PCM16 LE 24kHz)
  → new Int16Array(event.data)
  → Float32Array (cada muestra ÷ 32767)
  → AudioContext.createBuffer(1 canal, samples.length, 24000)
  → buffer.getChannelData(0).set(float32Samples)
  → BufferSourceNode.buffer = buffer
  → source.start(nextPlayTime)
  → nextPlayTime += buffer.duration
  → si nextPlayTime < audioContext.currentTime:
        nextPlayTime = audioContext.currentTime + 0.05  ← reset de cola atrasada
```

Encadena chunks sin gaps. El reset de 50ms evita que la cola explote si el tab queda en background.

### 4.3 Limpieza al colgar

```typescript
websocket.send(JSON.stringify({ type: "stop" }))
websocket.close()
workletNode.disconnect()
mediaStream.getTracks().forEach(t => t.stop())  // apaga la luz del micrófono
audioContext.close()
```

---

## 5. Componente `VoiceCallWidget`

### Estado

```typescript
type CallStatus = 'connecting' | 'listening' | 'speaking' | 'ended' | 'error'

const [status, setStatus]       = useState<CallStatus>('connecting')
const [transcript, setTranscript] = useState<TranscriptEntry[]>([])
const [errorMsg, setErrorMsg]   = useState<string>('')

// refs (no causan re-render):
// websocket, audioContext, workletNode, mediaStream, nextPlayTime
```

### Máquina de estados

```
connecting  → listening   (status JSON "connected" o "listening" del server)
listening   → speaking    (status JSON "speaking")
speaking    → listening   (status JSON "listening")
listening   → ended       (status JSON "ended" o websocket cierra)
*           → error       (JSON "error" o excepción de getUserMedia)
ended/error → [desmonta]
```

### UI

```
┌─────────────────────────────────────┐
│ [avatar] Camila          [● EN VIVO]│  ← header azul/navy (igual a ChatbotWidget)
│          Llamada de voz             │
├─────────────────────────────────────┤
│                                     │
│  Camila: Hola, soy Camila de...     │  ← burbujas iguales al ChatbotWidget
│                    Tú: Buenos días  │    (reutiliza clases CSS existentes)
│                                     │
│       [ 🎙 escuchando... ]          │  ← badge de status centrado, animado
│                                     │
├─────────────────────────────────────┤
│           [ 📵  Colgar ]            │  ← botón rojo centrado
└─────────────────────────────────────┘
```

Tamaño y posición idénticos a `ChatbotWidget` (misma hoja de estilos base, `.chatbot-widget`).

Badge de status:
- `connecting` → "Conectando…" (gris)
- `listening`  → "Escuchando…" (verde, pulso)
- `speaking`   → "Camila está hablando…" (azul, pulso)
- `ended`      → "Llamada finalizada"
- `error`      → mensaje de error en rojo

### Ciclo de vida

```
onMount:
  1. Abrir WebSocket (voice.api.ts)
  2. getUserMedia({ audio: true })  → si falla → status='error', mostrar mensaje
  3. new AudioContext()
  4. audioContext.audioWorklet.addModule(processorUrl)
        // processorUrl viene de: import processorUrl from '...pcm-processor.worklet.ts?url'
        // Vite resuelve el hash en build, mismo origen garantizado
  5. Conectar pipeline captura
  6. Escuchar mensajes WebSocket:
       binary → encolar playback
       JSON   → actualizar status / transcript / error

onUnmount / onColgar:
  → limpieza completa (ver 4.3)
```

---

## 6. Modificaciones al contact center

### `ContactCenterMenu.tsx`

Props nuevas: `onOpenCall: () => void`

```tsx
// Antes:
<a href={CONTACT_INFO.phoneHref} ...>Llamar</a>

// Después:
<button className="contact-center-menu__item" onClick={() => { onOpenCall(); onSelect(); }}>
  <span className="contact-center-menu__label">Llamar</span>
  <PhoneIcon size={24} />
</button>
```

### `ContactCenterButton.tsx`

```tsx
const [callOpen, setCallOpen] = useState(false)

// Solo uno abierto a la vez: chat O llamada
// Al abrir menú: cierra ambos
// Al abrir chat: cierra llamada
// Al abrir llamada: cierra chat

{callOpen && <VoiceCallWidget onClose={() => setCallOpen(false)} />}

<ContactCenterMenu
  onOpenChat={() => { setCallOpen(false); setOpen(false); setChatOpen(true) }}
  onOpenCall={() => { setChatOpen(false); setOpen(false); setCallOpen(true) }}
  onSelect={() => setOpen(false)}
/>
```

---

## 7. Persistencia en base de datos

No requiere cambios en el backend. El flujo existente ya cubre todo:

| Evento | Tool de Gemini | Tabla Supabase |
|---|---|---|
| Camila pide nombre/cédula/empresa/teléfono | `registrar_datos_cliente` | `clientes` |
| Llamada termina | `registrar_resumen_llamada` | `llamadas` |

`llamadas` guarda: `resumen`, `intention` (fria/calida/caliente), `score_lead` (0–100), `servicios_interes[]`, `recomendaciones`. Estos campos son suficientes para que un agente de WhatsApp retome la conversación en la fase siguiente.

---

## 8. Configuración de entorno

`VITE_API_BASE_URL` ya existe en `gotocloud-frontend/.env`. El widget deriva la URL del WebSocket de esta variable:

```typescript
const wsUrl = API_BASE_URL.replace(/^http/, 'ws') + '/web-stream'
// http://127.0.0.1:8000 → ws://127.0.0.1:8000/web-stream
// https://api.gotocloud.ai → wss://api.gotocloud.ai/web-stream
```

---

## 9. Manejo de errores

| Caso | Comportamiento |
|---|---|
| Usuario deniega micrófono | status='error', mensaje "Necesitamos acceso al micrófono para la llamada" |
| WebSocket falla al conectar | status='error', mensaje "No se pudo conectar con Camila" |
| Backend devuelve `{"type":"error"}` | status='error', muestra `message` del payload |
| Tab en background (audio atrasado) | nextPlayTime se resetea a currentTime+50ms, sin crash |
| Usuario cierra el widget sin colgar | onUnmount hace limpieza completa automáticamente |

---

## 10. Lo que NO está en scope

- Integración WhatsApp (fase siguiente)
- Mejoras del dashboard (fase siguiente)
- Autenticación / identificación del visitante antes de la llamada (Camila la recoge durante la conversación)
- Grabación de audio (solo transcript)
- Soporte multi-llamada simultánea (demo único usuario)
