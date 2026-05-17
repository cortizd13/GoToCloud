export type CallStatus = 'connecting' | 'listening' | 'speaking' | 'ended' | 'error';

export type TranscriptEntry = {
  id: string;
  role: 'user' | 'model';
  text: string;
};
