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
