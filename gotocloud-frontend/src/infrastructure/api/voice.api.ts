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
  private readonly callbacks: VoiceSessionCallbacks;
  private audioContext: AudioContext | null = null;
  private workletNode: AudioWorkletNode | null = null;
  private mediaStream: MediaStream | null = null;
  private nextPlayTime = 0;

  constructor(callbacks: VoiceSessionCallbacks) {
    this.callbacks = callbacks;
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
