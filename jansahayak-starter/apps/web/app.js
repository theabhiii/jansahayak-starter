const STORAGE_KEY = 'jansahayak_chats_v3';
const API_BASE_STORAGE_KEY = 'jansahayak_api_base';

const state = {
  chats: [],
  activeChatId: null,
  recognition: null,
  isRecording: false,
  voices: [],
};

function nowIso() {
  return new Date().toISOString();
}

function normalizeApiBase(base) {
  return String(base || '').trim().replace(/\/+$/, '');
}

function getDefaultApiBase() {
  const configured = normalizeApiBase(window.JANSAHAYAK_CONFIG?.apiBaseUrl);
  if (configured) return configured;
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://localhost:8000';
  }
  return '';
}

function resolveInitialApiBase() {
  const params = new URLSearchParams(window.location.search);
  const fromQuery = normalizeApiBase(params.get('apiBase'));
  if (fromQuery) return fromQuery;

  const fromStorage = normalizeApiBase(localStorage.getItem(API_BASE_STORAGE_KEY));
  if (fromStorage) return fromStorage;

  return getDefaultApiBase();
}

function getApiBase() {
  const input = document.getElementById('apiBase');
  const value = normalizeApiBase(input?.value);
  if (input && input.value !== value) {
    input.value = value;
  }
  if (value) {
    localStorage.setItem(API_BASE_STORAGE_KEY, value);
  } else {
    localStorage.removeItem(API_BASE_STORAGE_KEY);
  }
  return value;
}

function initializeApiBaseInput() {
  const input = document.getElementById('apiBase');
  if (!input) return;
  input.value = resolveInitialApiBase();
}

function shortTitle(text) {
  const normalized = (text || '').replace(/\s+/g, ' ').trim();
  if (!normalized) return 'New Conversation';
  return normalized.length > 38 ? `${normalized.slice(0, 38)}...` : normalized;
}

function uiLanguage(code) {
  if (!code) return 'en';
  const normalized = String(code).toLowerCase();
  if (normalized.startsWith('hi')) return 'hi';
  if (normalized.startsWith('bn')) return 'bn';
  if (normalized.startsWith('ta')) return 'ta';
  if (normalized.startsWith('te')) return 'te';
  if (normalized.startsWith('kn')) return 'kn';
  if (normalized.startsWith('ml')) return 'ml';
  if (normalized.startsWith('mr')) return 'mr';
  if (normalized.startsWith('gu')) return 'gu';
  if (normalized.startsWith('pa')) return 'pa';
  if (normalized.startsWith('od')) return 'od';
  if (normalized.startsWith('es')) return 'es';
  return 'en';
}

function uiText(key, languageCode) {
  const lang = uiLanguage(languageCode);
  const table = {
    en: {
      speakerAria: 'Read response aloud',
      speakerTitle: 'Read response aloud',
      speakerLatestOnly: 'Only the latest assistant response can be played',
      speakerUnsupported: 'Read response aloud (not supported for this language)',
      audioUnsupported: 'Audio playback is not supported for the current response language.',
      startPrompt: 'Start by asking about schemes, eligibility, grievances, or location-specific guidance.',
      assistantLabel: 'Assistant',
      deleteConfirm: 'Delete this chat permanently from local history?',
      apiUnreachable: 'Unable to reach API.',
      improveFirst: 'Send a message first, then use Improve.',
      improveFailed: 'Could not run improvement flow.',
      askFirstTts: 'Ask something first so I have text to send for TTS.',
      voiceStatus: 'Voice status',
      voiceFailed: 'Voice call failed.',
      voiceUnavailable: 'Voice input unavailable',
      stopVoice: 'Stop voice input',
      startVoice: 'Voice input',
      voiceError: 'Voice input error',
      thanks: 'Thank you. Your feedback is captured for quality improvement.',
      thinkingLabel: 'Model thinking',
      showThinking: 'Show thinking',
      hideThinking: 'Hide thinking',
      referencesLabel: 'References',
      openSource: 'Open Source',
      welcomeTitle: 'Welcome',
      welcomeLine1: '\u0928\u092E\u0938\u094D\u0924\u0947! JanSahayak \u092E\u0947\u0902 \u0906\u092A\u0915\u093E \u0938\u094D\u0935\u093E\u0917\u0924 \u0939\u0948\u0964',
      welcomeLine2: '\u09B8\u09CD\u09AC\u09BE\u0997\u09A4\u09AE! \u09B8\u09B0\u0995\u09BE\u09B0\u09BF \u09AA\u09B0\u09BF\u09B7\u09C7\u09AC\u09BE \u099C\u09BE\u09A8\u09A4\u09C7 \u09AA\u09CD\u09B0\u09B6\u09CD\u09A8 \u0995\u09B0\u09C1\u09A8\u0964',
      welcomeLine3: '\u0BB5\u0BA3\u0B95\u0BCD\u0B95\u0BAE\u0BCD! \u0BA4\u0BBF\u0B9F\u0BCD\u0B9F\u0B99\u0BCD\u0B95\u0BB3\u0BCD \u0BAE\u0BB1\u0BCD\u0BB1\u0BC1\u0BAE\u0BCD \u0BA4\u0B95\u0BC1\u0BA4\u0BBF \u0BAA\u0BB1\u0BCD\u0BB1\u0BBF \u0B95\u0BC7\u0BB3\u0BC1\u0B99\u0BCD\u0B95\u0BB3\u0BCD.',
      welcomeLine4: '\u0C38\u0C4D\u0C35\u0C3E\u0C17\u0C24\u0C02! \u0C2A\u0C25\u0C15\u0C3E\u0C32\u0C41, \u0C05\u0C30\u0C4D\u0C39\u0C24, \u0C2B\u0C3F\u0C30\u0C4D\u0C2F\u0C3E\u0C26\u0C41\u0C32\u0C2A\u0C48 \u0C05\u0C21\u0C17\u0C02\u0C21\u0C3F.',
      feedbackLabel: 'Was this response helpful?',
      like: 'Helpful',
      dislike: 'Not helpful',
      feedbackSaved: 'Thanks, feedback saved.',
      improveReady: 'Improved answer:',
      improveFailedInline: 'Could not run improve flow.',
      feedbackMissingContext: 'What was missing or incorrect?',
      feedbackStyle: 'Preferred response style',
      feedbackContext: 'Any context to include (location, category, beneficiary)?',
      feedbackStyleShort: 'Short summary',
      feedbackStyleStep: 'Step-by-step',
      feedbackStyleDetailed: 'Detailed explanation',
      submitFeedback: 'Submit',
      cancel: 'Cancel',
      feedbackPromptTitle: 'Help me improve this answer',
    },
    hi: {
      speakerAria: 'à¤‰à¤¤à¥à¤¤à¤° à¤¸à¥à¤¨à¥‡à¤‚',
      speakerTitle: 'à¤‰à¤¤à¥à¤¤à¤° à¤¸à¥à¤¨à¥‡à¤‚',
      speakerLatestOnly: 'à¤•à¥‡à¤µà¤² à¤¨à¤µà¥€à¤¨à¤¤à¤® à¤¸à¤¹à¤¾à¤¯à¤• à¤‰à¤¤à¥à¤¤à¤° à¤šà¤²à¤¾à¤¯à¤¾ à¤œà¤¾ à¤¸à¤•à¤¤à¤¾ à¤¹à¥ˆ',
      speakerUnsupported: 'à¤‰à¤¤à¥à¤¤à¤° à¤¸à¥à¤¨à¥‡à¤‚ (à¤‡à¤¸ à¤­à¤¾à¤·à¤¾ à¤•à¥‡ à¤²à¤¿à¤ à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¨à¤¹à¥€à¤‚)',
      audioUnsupported: 'à¤®à¥Œà¤œà¥‚à¤¦à¤¾ à¤‰à¤¤à¥à¤¤à¤° à¤­à¤¾à¤·à¤¾ à¤•à¥‡ à¤²à¤¿à¤ à¤‘à¤¡à¤¿à¤¯à¥‹ à¤ªà¥à¤²à¥‡à¤¬à¥ˆà¤• à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¨à¤¹à¥€à¤‚ à¤¹à¥ˆà¥¤',
      startPrompt: 'à¤¯à¥‹à¤œà¤¨à¤¾à¤“à¤‚, à¤ªà¤¾à¤¤à¥à¤°à¤¤à¤¾, à¤¶à¤¿à¤•à¤¾à¤¯à¤¤ à¤¯à¤¾ à¤¸à¥à¤¥à¤¾à¤¨-à¤†à¤§à¤¾à¤°à¤¿à¤¤ à¤®à¤¾à¤°à¥à¤—à¤¦à¤°à¥à¤¶à¤¨ à¤•à¥‡ à¤¬à¤¾à¤°à¥‡ à¤®à¥‡à¤‚ à¤ªà¥‚à¤›à¤¨à¤¾ à¤¶à¥à¤°à¥‚ à¤•à¤°à¥‡à¤‚à¥¤',
      assistantLabel: '\u0938\u0939\u093E\u092F\u0915',
      deleteConfirm: 'à¤•à¥à¤¯à¤¾ à¤†à¤ª à¤‡à¤¸ à¤šà¥ˆà¤Ÿ à¤•à¥‹ à¤¸à¥à¤¥à¤¾à¤¨à¥€à¤¯ à¤‡à¤¤à¤¿à¤¹à¤¾à¤¸ à¤¸à¥‡ à¤¸à¥à¤¥à¤¾à¤¯à¥€ à¤°à¥‚à¤ª à¤¸à¥‡ à¤¹à¤Ÿà¤¾à¤¨à¤¾ à¤šà¤¾à¤¹à¤¤à¥‡ à¤¹à¥ˆà¤‚?',
      apiUnreachable: 'API à¤¤à¤• à¤ªà¤¹à¥à¤‚à¤š à¤¨à¤¹à¥€à¤‚ à¤¹à¥‹ à¤ªà¤¾à¤ˆà¥¤',
      improveFirst: 'à¤ªà¤¹à¤²à¥‡ à¤à¤• à¤¸à¤‚à¤¦à¥‡à¤¶ à¤­à¥‡à¤œà¥‡à¤‚, à¤«à¤¿à¤° Improve à¤•à¤¾ à¤‰à¤ªà¤¯à¥‹à¤— à¤•à¤°à¥‡à¤‚à¥¤',
      improveFailed: 'à¤¸à¥à¤§à¤¾à¤° à¤ªà¥à¤°à¤•à¥à¤°à¤¿à¤¯à¤¾ à¤ªà¥‚à¤°à¥€ à¤¨à¤¹à¥€à¤‚ à¤¹à¥‹ à¤¸à¤•à¥€à¥¤',
      askFirstTts: 'à¤ªà¤¹à¤²à¥‡ à¤•à¥à¤› à¤ªà¥‚à¤›à¥‡à¤‚ à¤¤à¤¾à¤•à¤¿ à¤®à¥ˆà¤‚ TTS à¤•à¥‡ à¤²à¤¿à¤ à¤ªà¤¾à¤  à¤­à¥‡à¤œ à¤¸à¤•à¥‚à¤‚à¥¤',
      voiceStatus: 'à¤†à¤µà¤¾à¤œà¤¼ à¤¸à¥à¤¥à¤¿à¤¤à¤¿',
      voiceFailed: 'Voice à¤•à¥‰à¤² à¤µà¤¿à¤«à¤² à¤°à¤¹à¤¾à¥¤',
      voiceUnavailable: 'à¤µà¥‰à¤¯à¤¸ à¤‡à¤¨à¤ªà¥à¤Ÿ à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¨à¤¹à¥€à¤‚',
      stopVoice: 'à¤µà¥‰à¤¯à¤¸ à¤‡à¤¨à¤ªà¥à¤Ÿ à¤°à¥‹à¤•à¥‡à¤‚',
      startVoice: 'à¤µà¥‰à¤¯à¤¸ à¤‡à¤¨à¤ªà¥à¤Ÿ',
      voiceError: 'à¤µà¥‰à¤¯à¤¸ à¤‡à¤¨à¤ªà¥à¤Ÿ à¤¤à¥à¤°à¥à¤Ÿà¤¿',
      thanks: 'à¤§à¤¨à¥à¤¯à¤µà¤¾à¤¦à¥¤ à¤†à¤ªà¤•à¥€ à¤ªà¥à¤°à¤¤à¤¿à¤•à¥à¤°à¤¿à¤¯à¤¾ à¤—à¥à¤£à¤µà¤¤à¥à¤¤à¤¾ à¤¸à¥à¤§à¤¾à¤° à¤•à¥‡ à¤²à¤¿à¤ à¤¦à¤°à¥à¤œ à¤•à¤° à¤²à¥€ à¤—à¤ˆ à¤¹à¥ˆà¥¤',
    },
    bn: {
      startPrompt: '\u09B8\u09CD\u0995\u09BF\u09AE, \u09AF\u09CB\u0997\u09CD\u09AF\u09A4\u09BE, \u0985\u09AD\u09BF\u09AF\u09CB\u0997 \u09AC\u09BE \u0985\u09AC\u09B8\u09CD\u09A5\u09BE\u09A8\u09AD\u09BF\u09A4\u09CD\u09A4\u09BF\u0995 \u09A8\u09BF\u09B0\u09CD\u09A6\u09C7\u09B6\u09A8\u09BE \u09B8\u09AE\u09CD\u09AA\u09B0\u09CD\u0995\u09C7 \u09AA\u09CD\u09B0\u09B6\u09CD\u09A8 \u0995\u09B0\u09C7 \u09B6\u09C1\u09B0\u09C1 \u0995\u09B0\u09C1\u09A8\u0964',
    },
    ta: {
      startPrompt: '\u0BA4\u0BBF\u0B9F\u0BCD\u0B9F\u0B99\u0BCD\u0B95\u0BB3\u0BCD, \u0BA4\u0B95\u0BC1\u0BA4\u0BBF, \u0BAA\u0BC1\u0B95\u0BBE\u0BB0\u0BCD\u0B95\u0BB3\u0BCD \u0B85\u0BB2\u0BCD\u0BB2\u0BA4\u0BC1 \u0B87\u0B9F\u0BB5\u0BBE\u0BB0\u0BBF\u0BAF\u0BBE\u0BA9 \u0BB5\u0BB4\u0BBF\u0B95\u0BBE\u0B9F\u0BCD\u0B9F\u0BB2\u0BCD \u0BAA\u0BB1\u0BCD\u0BB1\u0BBF \u0B95\u0BC7\u0B9F\u0BCD\u0B9F\u0BC1 \u0BA4\u0BCA\u0B9F\u0B99\u0BCD\u0B95\u0BC1\u0B99\u0BCD\u0B95\u0BB3\u0BCD.',
    },
    te: {
      startPrompt: '\u0C2A\u0C25\u0C15\u0C3E\u0C32\u0C41, \u0C05\u0C30\u0C4D\u0C39\u0C24, \u0C2B\u0C3F\u0C30\u0C4D\u0C2F\u0C3E\u0C26\u0C41\u0C32\u0C41 \u0C32\u0C47\u0C26\u0C3E \u0C38\u0C4D\u0C25\u0C3E\u0C28\u0C3F\u0C15 \u0C2E\u0C3E\u0C30\u0C4D\u0C17\u0C26\u0C30\u0C4D\u0C36\u0C15\u0C24\u0C4D\u0C35\u0C02 \u0C17\u0C41\u0C30\u0C3F\u0C02\u0C1A\u0C3F \u0C05\u0C21\u0C17\u0C3F \u0C2A\u0C4D\u0C30\u0C3E\u0C30\u0C02\u0C2D\u0C3F\u0C02\u0C1A\u0C02\u0C21\u0C3F.',
    },
    kn: {
      startPrompt: '\u0CAF\u0CCB\u0C9C\u0CA8\u0CC6\u0C97\u0CB3\u0CC1, \u0C85\u0CB0\u0CCD\u0CB9\u0CA4\u0CC6, \u0CA6\u0CC2\u0CB0\u0CC1\u0C97\u0CB3\u0CC1 \u0C85\u0CA5\u0CB5\u0CBE \u0CB8\u0CCD\u0CA5\u0CB3\u0CBE\u0CA7\u0CBE\u0CB0\u0CBF\u0CA4 \u0CAE\u0CBE\u0CB0\u0CCD\u0C97\u0CA6\u0CB0\u0CCD\u0CB6\u0CA8\u0C95\u0CCD\u0C95\u0CBE\u0C97\u0CBF \u0C95\u0CC7\u0CB3\u0CC1\u0CB5\u0CC1\u0CA6\u0CB0\u0CBF\u0C82\u0CA6 \u0CAA\u0CCD\u0CB0\u0CBE\u0CB0\u0C82\u0CAD\u0CBF\u0CB8\u0CBF.',
    },
    ml: {
      startPrompt: '\u0D2A\u0D26\u0D4D\u0D27\u0D24\u0D3F\u0D15\u0D7E, \u0D05\u0D30\u0D4D\u0D39\u0D24, \u0D2A\u0D30\u0D3E\u0D24\u0D3F\u0D15\u0D7E \u0D05\u0D25\u0D35\u0D3E \u0D38\u0D4D\u0D25\u0D32\u0D3E\u0D27\u0D3F\u0D37\u0D4D\u0D20\u0D3F\u0D24 \u0D2E\u0D3E\u0D7C\u0D17\u0D4D\u0D17\u0D28\u0D3F\u0D7C\u0D26\u0D4D\u0D26\u0D47\u0D36\u0D02 \u0D15\u0D41\u0D31\u0D3F\u0D1A\u0D4D\u0D1A\u0D4D \u0D1A\u0D4B\u0D26\u0D3F\u0D1A\u0D4D\u0D1A\u0D4D \u0D24\u0D41\u0D1F\u0D19\u0D4D\u0D19\u0D41\u0D15.',
    },
    mr: {
      startPrompt: '\u092F\u094B\u091C\u0928\u093E, \u092A\u093E\u0924\u094D\u0930\u0924\u093E, \u0924\u0915\u094D\u0930\u093E\u0930\u0940 \u0915\u093F\u0902\u0935\u093E \u0938\u094D\u0925\u093E\u0928-\u0935\u093F\u0936\u093F\u0937\u094D\u091F \u092E\u093E\u0930\u094D\u0917\u0926\u0930\u094D\u0936\u0928\u093E\u092C\u0926\u094D\u0926\u0932 \u0935\u093F\u091A\u093E\u0930\u0942\u0928 \u0938\u0941\u0930\u0941\u0935\u093E\u0924 \u0915\u0930\u093E.',
    },
    gu: {
      startPrompt: '\u0AAF\u0ACB\u0A9C\u0AA8\u0ABE\u0A93, \u0AAA\u0ABE\u0AA4\u0ACD\u0AB0\u0AA4\u0ABE, \u0AAB\u0AB0\u0ABF\u0AAF\u0ABE\u0AA6\u0ACB \u0A85\u0AA5\u0AB5\u0ABE \u0AB8\u0ACD\u0AA5\u0ABE\u0AA8-\u0A86\u0AA7\u0ABE\u0AB0\u0ABF\u0AA4 \u0AAE\u0ABE\u0AB0\u0ACD\u0A97\u0AA6\u0AB0\u0ACD\u0AB6\u0AA8 \u0AB5\u0ABF\u0AB6\u0AC7 \u0AAA\u0AC2\u0A9B\u0AC0\u0AA8\u0AC7 \u0AB6\u0AB0\u0AC1\u0A86\u0AA4 \u0A95\u0AB0\u0ACB.',
    },
    pa: {
      startPrompt: '\u0A2F\u0A4B\u0A1C\u0A28\u0A3E\u0A35\u0A3E\u0A02, \u0A2F\u0A4B\u0A17\u0A24\u0A3E, \u0A38\u0A3C\u0A3F\u0A15\u0A3E\u0A07\u0A24\u0A3E\u0A02 \u0A1C\u0A3E\u0A02 \u0A38\u0A25\u0A3E\u0A28-\u0A05\u0A27\u0A3E\u0A30\u0A3F\u0A24 \u0A2E\u0A3E\u0A30\u0A17\u0A26\u0A30\u0A38\u0A3C\u0A28 \u0A2C\u0A3E\u0A30\u0A47 \u0A2A\u0A41\u0A1B \u0A15\u0A47 \u0A38\u0A3C\u0A41\u0A30\u0A42 \u0A15\u0A30\u0A4B.',
    },
    od: {
      startPrompt: '\u0B2F\u0B4B\u0B1C\u0B28\u0B3E, \u0B2F\u0B4B\u0B17\u0B4D\u0B5F\u0B24\u0B3E, \u0B05\u0B2D\u0B3F\u0B2F\u0B4B\u0B17 \u0B15\u0B3F\u0B2E\u0B4D\u0B2C\u0B3E \u0B38\u0B4D\u0B25\u0B3E\u0B28-\u0B2D\u0B3F\u0B24\u0B4D\u0B24\u0B3F\u0B15 \u0B2E\u0B3E\u0B30\u0B4D\u0B17\u0B26\u0B30\u0B4D\u0B36\u0B28 \u0B2C\u0B3F\u0B37\u0B5F\u0B30\u0B47 \u0B2A\u0B1A\u0B3E\u0B30\u0B3F \u0B06\u0B30\u0B2E\u0B4D\u0B2D \u0B15\u0B30\u0B28\u0B4D\u0B24\u0B41\u0964',
    },
    es: {
      speakerAria: 'Leer respuesta en voz alta',
      speakerTitle: 'Leer respuesta en voz alta',
      speakerLatestOnly: 'Solo se puede reproducir la respuesta mÃ¡s reciente del asistente',
      speakerUnsupported: 'Leer respuesta en voz alta (no compatible para este idioma)',
      audioUnsupported: 'La reproducciÃ³n de audio no es compatible con el idioma de la respuesta actual.',
      startPrompt: 'Empieza preguntando por esquemas, elegibilidad, quejas o guÃ­a por ubicaciÃ³n.',
      assistantLabel: 'Asistente',
      deleteConfirm: 'Â¿Eliminar este chat permanentemente del historial local?',
      apiUnreachable: 'No se pudo conectar con la API.',
      improveFirst: 'Primero envÃ­a un mensaje y luego usa Improve.',
      improveFailed: 'No se pudo completar la mejora.',
      askFirstTts: 'Primero pregunta algo para enviar texto a TTS.',
      voiceStatus: 'Estado de voz',
      voiceFailed: 'La llamada de voz fallÃ³.',
      voiceUnavailable: 'Entrada de voz no disponible',
      stopVoice: 'Detener entrada de voz',
      startVoice: 'Entrada de voz',
      voiceError: 'Error de entrada de voz',
      thanks: 'Gracias. Tu feedback fue guardado para mejorar la calidad.',
    },
  };

  return table[lang][key] || table.en[key] || key;
}

function createChat(seedTitle = 'New Conversation') {
  const id = `session-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
  return {
    id,
    title: seedTitle,
    updatedAt: nowIso(),
    messages: [],
    lastQuestion: null,
    lastAnswer: null,
    lastAnswerLanguage: 'en-IN',
    lastFeedbackToken: null,
    lastResponse: null,
  };
}

function getActiveChat() {
  return state.chats.find((c) => c.id === state.activeChatId) || null;
}

function saveChats() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ chats: state.chats, activeChatId: state.activeChatId }));
}

function loadChats() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) throw new Error('No local storage data');
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed.chats) && parsed.chats.length) {
      state.chats = parsed.chats;
      state.activeChatId = parsed.activeChatId && parsed.chats.some((c) => c.id === parsed.activeChatId)
        ? parsed.activeChatId
        : parsed.chats[0].id;
      return;
    }
  } catch (_err) {
    // fallback to a default chat
  }

  const initial = createChat();
  state.chats = [initial];
  state.activeChatId = initial.id;
  saveChats();
}

function escapeHtml(unsafe) {
  return (unsafe || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function getMostRecentAssistantMessage(chat) {
  if (!chat) return null;
  for (let i = chat.messages.length - 1; i >= 0; i -= 1) {
    if (chat.messages[i].type === 'bot') return chat.messages[i];
  }
  return null;
}

function parseAssistantResponse(rawText) {
  const original = String(rawText || '');
  let text = original;
  let thinking = '';

  const thinkTag = text.match(/<think>([\s\S]*?)<\/think>/i);
  if (thinkTag) {
    thinking = thinkTag[1].trim();
    text = text.replace(thinkTag[0], '').trim();
  }

  if (!thinking) {
    const fencedThinking = text.match(/```(?:thinking|reasoning|thoughts?)\s*([\s\S]*?)```/i);
    if (fencedThinking) {
      thinking = fencedThinking[1].trim();
      text = text.replace(fencedThinking[0], '').trim();
    }
  }

  if (!thinking) {
    const markerSplit = text.match(/(?:^|\n)(?:Reasoning|Thinking|Thought process)\s*:?\s*([\s\S]*?)(?:\n(?:Final Answer|Answer)\s*:)/i);
    if (markerSplit) {
      thinking = markerSplit[1].trim();
      text = text.replace(markerSplit[0], '\n').trim();
      text = text.replace(/^(Final Answer|Answer)\s*:\s*/i, '').trim();
    }
  }

  return {
    answer: text || original,
    thinking,
  };
}

function normalizeSources(sources) {
  if (!Array.isArray(sources)) return [];
  return sources
    .filter((src) => src && typeof src.url === 'string' && /^https?:\/\//i.test(src.url))
    .map((src) => ({
      id: src.id || '',
      title: src.title || src.url,
      url: src.url,
    }));
}

function buildFormattedAnswerNode(answerText) {
  const container = document.createElement('div');
  container.className = 'answer-formatted';
  const lines = String(answerText || '').split('\n');
  let currentList = null;

  lines.forEach((lineRaw) => {
    const line = lineRaw.trim();
    if (!line) {
      currentList = null;
      return;
    }

    if (line.startsWith('- ')) {
      if (!currentList) {
        currentList = document.createElement('ul');
        currentList.className = 'answer-list';
        container.appendChild(currentList);
      }
      const li = document.createElement('li');
      li.textContent = line.slice(2).trim();
      currentList.appendChild(li);
      return;
    }

    currentList = null;
    const p = document.createElement('p');
    p.className = 'answer-line';
    p.textContent = line;
    container.appendChild(p);
  });

  return container;
}

function buildReferencesNode(sources, languageCode) {
  const list = normalizeSources(sources);
  if (!list.length) return null;

  const wrap = document.createElement('div');
  wrap.className = 'references-wrap';

  const label = document.createElement('div');
  label.className = 'references-label';
  label.textContent = uiText('referencesLabel', languageCode);
  wrap.appendChild(label);

  list.forEach((src) => {
    const row = document.createElement('div');
    row.className = 'reference-row';

    const title = document.createElement('div');
    title.className = 'reference-title';
    title.textContent = src.title;
    row.appendChild(title);

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'reference-btn secondary';
    btn.textContent = uiText('openSource', languageCode);
    btn.title = src.url;
    btn.addEventListener('click', () => window.open(src.url, '_blank', 'noopener,noreferrer'));
    row.appendChild(btn);

    wrap.appendChild(row);
  });

  return wrap;
}

function normalizeLangForSpeech(code) {
  if (!code) return 'en-IN';
  return code;
}

function detectSpeechLanguageCode(text, fallback = 'en-IN') {
  const value = String(text || '');
  if (!value.trim()) return fallback;

  const has = (re) => re.test(value);
  if (has(/[\u0B80-\u0BFF]/)) return 'ta-IN';
  if (has(/[\u0C00-\u0C7F]/)) return 'te-IN';
  if (has(/[\u0C80-\u0CFF]/)) return 'kn-IN';
  if (has(/[\u0D00-\u0D7F]/)) return 'ml-IN';
  if (has(/[\u0980-\u09FF]/)) return 'bn-IN';
  if (has(/[\u0A80-\u0AFF]/)) return 'gu-IN';
  if (has(/[\u0B00-\u0B7F]/)) return 'od-IN';
  if (has(/[\u0A00-\u0A7F]/)) return 'pa-IN';
  if (has(/[\u0900-\u097F]/)) return 'hi-IN';
  if (has(/[\u0600-\u06FF]/)) return 'ur-IN';
  if (has(/[áéíóúñüÁÉÍÓÚÑÜ]/)) return 'es-ES';
  return fallback;
}

function getPreferredRecognitionLanguage() {
  const chat = getActiveChat();
  const chatLang = normalizeLangForSpeech(chat?.lastAnswerLanguage);
  if (chatLang) return chatLang;
  const browserLang = normalizeLangForSpeech(navigator.language || '');
  return browserLang || 'en-IN';
}

function hasVoiceForLanguage(languageCode) {
  if (!('speechSynthesis' in window)) return false;
  const target = normalizeLangForSpeech(languageCode).toLowerCase();
  const [primary] = target.split('-');
  const voices = state.voices.length ? state.voices : window.speechSynthesis.getVoices();
  if (!voices.length) return false;
  return voices.some((v) => {
    const voiceLang = (v.lang || '').toLowerCase();
    return voiceLang === target || voiceLang.startsWith(`${primary}-`) || voiceLang === primary;
  });
}

function speakText(text, languageCode) {
  if (!('speechSynthesis' in window)) return false;
  if (!hasVoiceForLanguage(languageCode)) return false;

  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = normalizeLangForSpeech(languageCode);
  utterance.rate = 1;
  utterance.pitch = 1;
  window.speechSynthesis.speak(utterance);
  return true;
}

function buildAudioDataUrl(audioBase64, audioMimeType = 'audio/mpeg') {
  if (!audioBase64) return null;
  return `data:${audioMimeType};base64,${audioBase64}`;
}

function playAudioBase64(audioBase64, audioMimeType) {
  const dataUrl = buildAudioDataUrl(audioBase64, audioMimeType);
  if (!dataUrl) return false;
  try {
    const audio = new Audio(dataUrl);
    audio.play().catch(() => {});
    return true;
  } catch (_) {
    return false;
  }
}

function renderChatList() {
  const list = document.getElementById('chatList');
  list.innerHTML = '';

  state.chats
    .slice()
    .sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt))
    .forEach((chat) => {
      const item = document.createElement('button');
      item.type = 'button';
      item.className = `chat-item ${chat.id === state.activeChatId ? 'active' : ''}`;
      item.innerHTML = `
        <div class="chat-title">${escapeHtml(chat.title)}</div>
        <div class="chat-time">${new Date(chat.updatedAt).toLocaleString()}</div>
      `;
      item.addEventListener('click', () => {
        state.activeChatId = chat.id;
        saveChats();
        renderAll();
      });
      list.appendChild(item);
    });
}

function createSpeakerButton(chat, message, isMostRecentBot) {
  const languageCode = message.languageCode || chat.lastAnswerLanguage || 'en-IN';
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'voice-btn secondary';
  btn.setAttribute('aria-label', uiText('speakerAria', languageCode));
  btn.title = uiText('speakerTitle', languageCode);
  btn.textContent = '\uD83D\uDD0A';

  const supported = hasVoiceForLanguage(languageCode);

  if (!isMostRecentBot || !supported) {
    btn.disabled = true;
    btn.title = !isMostRecentBot ? uiText('speakerLatestOnly', languageCode) : uiText('speakerUnsupported', languageCode);
    return btn;
  }

  btn.addEventListener('click', () => {
    const latest = getMostRecentAssistantMessage(chat);
    if (!latest) return;
    const parsed = parseAssistantResponse(latest.text);
    const ok = (latest.audioStatus === 'ok' && playAudioBase64(latest.audioBase64, latest.audioMimeType))
      || speakText(parsed.answer, latest.languageCode || languageCode);
    if (!ok) {
      appendMessage(uiText('audioUnsupported', languageCode), 'bot', { languageCode });
    }
  });
  return btn;
}

function buildFeedbackReason(details) {
  const missing = (details.missing || '').trim();
  const style = (details.style || '').trim();
  const extra = (details.extra || '').trim();
  return [
    `Missing/Incorrect: ${missing || 'N/A'}`,
    `Preferred style: ${style || 'N/A'}`,
    `Additional context: ${extra || 'N/A'}`,
  ].join('\n');
}

function setMessageFeedbackState(chat, messageTs, patch) {
  const target = chat.messages.find((m) => m.ts === messageTs);
  if (!target) return;
  Object.assign(target, patch);
  saveChats();
  renderAll();
}

async function submitMessageFeedback(chat, message, feedback, details = null) {
  const apiBase = getApiBase();
  const languageCode = message.languageCode || chat.lastAnswerLanguage || 'en-IN';

  if (!message.feedbackToken || !message.originalQuestion) {
    appendMessage(uiText('improveFailedInline', languageCode), 'bot', { languageCode });
    return;
  }

  try {
    setMessageFeedbackState(chat, message.ts, { feedbackSubmitted: true, feedbackKind: feedback, feedbackFormOpen: false });

    const response = await fetch(`${apiBase}/chat/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: chat.id,
        feedback_token: message.feedbackToken,
        original_question: message.originalQuestion,
        original_answer: message.text,
        feedback,
        reason: details ? buildFeedbackReason(details) : null,
        language_code: languageCode,
      }),
    });

    if (!response.ok) {
      throw new Error(`Feedback failed with ${response.status}`);
    }

    if (feedback === 'negative') {
      const data = await response.json();
      if (data?.improved_answer) {
        appendMessage(`${uiText('improveReady', languageCode)}\n${data.improved_answer}`, 'bot', { languageCode });
      }
    }
  } catch (err) {
    setMessageFeedbackState(chat, message.ts, { feedbackSubmitted: false, feedbackKind: null });
    appendMessage(`${uiText('improveFailedInline', languageCode)} ${err.message}`, 'bot', { languageCode });
  }
}

function buildFeedbackForm(chat, message) {
  const languageCode = message.languageCode || chat.lastAnswerLanguage || 'en-IN';
  const form = document.createElement('div');
  form.className = 'feedback-form';

  const title = document.createElement('h4');
  title.textContent = uiText('feedbackPromptTitle', languageCode);
  form.appendChild(title);

  const missing = document.createElement('textarea');
  missing.placeholder = uiText('feedbackMissingContext', languageCode);
  missing.setAttribute('aria-label', uiText('feedbackMissingContext', languageCode));
  form.appendChild(missing);

  const style = document.createElement('select');
  style.setAttribute('aria-label', uiText('feedbackStyle', languageCode));
  [uiText('feedbackStyleShort', languageCode), uiText('feedbackStyleStep', languageCode), uiText('feedbackStyleDetailed', languageCode)]
    .forEach((label) => {
      const option = document.createElement('option');
      option.value = label;
      option.textContent = label;
      style.appendChild(option);
    });
  form.appendChild(style);

  const extra = document.createElement('textarea');
  extra.placeholder = uiText('feedbackContext', languageCode);
  extra.setAttribute('aria-label', uiText('feedbackContext', languageCode));
  form.appendChild(extra);

  const actions = document.createElement('div');
  actions.className = 'feedback-actions';

  const submit = document.createElement('button');
  submit.type = 'button';
  submit.className = 'primary';
  submit.textContent = uiText('submitFeedback', languageCode);
  submit.addEventListener('click', async () => {
    await submitMessageFeedback(chat, message, 'negative', {
      missing: missing.value,
      style: style.value,
      extra: extra.value,
    });
  });
  actions.appendChild(submit);

  const cancel = document.createElement('button');
  cancel.type = 'button';
  cancel.className = 'secondary';
  cancel.textContent = uiText('cancel', languageCode);
  cancel.addEventListener('click', () => {
    setMessageFeedbackState(chat, message.ts, { feedbackFormOpen: false });
  });
  actions.appendChild(cancel);

  form.appendChild(actions);
  return form;
}

function buildFeedbackRow(chat, message) {
  if (message.type !== 'bot') return null;
  if (Array.isArray(message.followUpOptions) && message.followUpOptions.length) return null;
  const languageCode = message.languageCode || chat.lastAnswerLanguage || 'en-IN';
  const row = document.createElement('div');
  row.className = 'feedback-row';

  if (message.feedbackSubmitted) {
    const done = document.createElement('span');
    done.className = 'feedback-status';
    done.textContent = uiText('feedbackSaved', languageCode);
    row.appendChild(done);
    return row;
  }

  const label = document.createElement('span');
  label.className = 'feedback-status';
  label.textContent = uiText('feedbackLabel', languageCode);
  row.appendChild(label);

  const likeBtn = document.createElement('button');
  likeBtn.type = 'button';
  likeBtn.className = 'feedback-btn secondary';
  likeBtn.textContent = `ðŸ‘ ${uiText('like', languageCode)}`;
  likeBtn.setAttribute('aria-label', uiText('like', languageCode));
  likeBtn.addEventListener('click', async () => {
    await submitMessageFeedback(chat, message, 'positive');
  });
  row.appendChild(likeBtn);

  const dislikeBtn = document.createElement('button');
  dislikeBtn.type = 'button';
  dislikeBtn.className = 'feedback-btn danger';
  dislikeBtn.textContent = `ðŸ‘Ž ${uiText('dislike', languageCode)}`;
  dislikeBtn.setAttribute('aria-label', uiText('dislike', languageCode));
  dislikeBtn.addEventListener('click', () => {
    setMessageFeedbackState(chat, message.ts, { feedbackFormOpen: true });
  });
  row.appendChild(dislikeBtn);

  return row;
}

function buildFollowUpOptionsNode(message) {
  const options = Array.isArray(message.followUpOptions) ? message.followUpOptions : [];
  if (!options.length) return null;
  const wrap = document.createElement('div');
  wrap.className = 'followup-options';

  options.forEach((opt) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'followup-option secondary';
    const label = opt.label || opt.value || '';
    const value = opt.value || label;
    btn.textContent = label;
    btn.setAttribute('aria-label', label);
    btn.addEventListener('click', async () => {
      await sendMessage(value, { forceLanguageCode: message.languageCode || getActiveChat()?.lastAnswerLanguage || null });
    });
    wrap.appendChild(btn);
  });
  return wrap;
}

function buildWelcomeCard(languageCode) {
  const card = document.createElement('div');
  card.className = 'welcome-card';

  const title = document.createElement('div');
  title.className = 'welcome-title';
  title.textContent = uiText('welcomeTitle', languageCode || 'en-IN');
  card.appendChild(title);

  const lines = document.createElement('div');
  lines.className = 'welcome-lines';
  ['welcomeLine1', 'welcomeLine2', 'welcomeLine3', 'welcomeLine4'].forEach((k) => {
    const row = document.createElement('div');
    row.textContent = uiText(k, languageCode || 'en-IN');
    lines.appendChild(row);
  });
  card.appendChild(lines);
  return card;
}

function renderMessages() {
  const messages = document.getElementById('messages');
  const debug = document.getElementById('debugMeta');
  messages.innerHTML = '';
  const chat = getActiveChat();

  if (!chat) {
    debug.textContent = 'No active chat selected.';
    return;
  }

  const latestBotMessage = getMostRecentAssistantMessage(chat);

  if (!chat.messages.length) {
    messages.appendChild(buildWelcomeCard(chat.lastAnswerLanguage || 'en-IN'));
    const info = document.createElement('div');
    info.className = 'message bot';
    info.textContent = uiText('startPrompt', chat.lastAnswerLanguage || 'en-IN');
    messages.appendChild(info);
  } else {
    chat.messages.forEach((msg) => {
      const div = document.createElement('div');
      div.className = `message ${msg.type}`;

      if (msg.type === 'bot') {
        const parsed = parseAssistantResponse(msg.text);
        const head = document.createElement('div');
        head.className = 'message-head';

        const label = document.createElement('span');
        label.className = 'message-label';
        label.textContent = uiText('assistantLabel', msg.languageCode || chat.lastAnswerLanguage || 'en-IN');
        head.appendChild(label);

        const actions = document.createElement('div');
        actions.className = 'message-actions';

        if (parsed.thinking) {
          const thinkingToggle = document.createElement('button');
          thinkingToggle.type = 'button';
          thinkingToggle.className = 'thinking-toggle secondary';
          thinkingToggle.textContent = uiText('showThinking', msg.languageCode || chat.lastAnswerLanguage || 'en-IN');
          thinkingToggle.title = uiText('showThinking', msg.languageCode || chat.lastAnswerLanguage || 'en-IN');
          thinkingToggle.setAttribute('aria-expanded', 'false');
          actions.appendChild(thinkingToggle);

          const thinkingWrap = document.createElement('div');
          thinkingWrap.className = 'thinking-wrap';
          thinkingWrap.hidden = true;

          const thinkingLabel = document.createElement('div');
          thinkingLabel.className = 'thinking-label';
          thinkingLabel.textContent = uiText('thinkingLabel', msg.languageCode || chat.lastAnswerLanguage || 'en-IN');

          const thinkingBody = document.createElement('div');
          thinkingBody.className = 'thinking-body';
          thinkingBody.textContent = parsed.thinking;

          thinkingWrap.appendChild(thinkingLabel);
          thinkingWrap.appendChild(thinkingBody);
          div.appendChild(thinkingWrap);

          thinkingToggle.addEventListener('click', () => {
            const isOpen = !thinkingWrap.hidden;
            thinkingWrap.hidden = isOpen;
            thinkingToggle.setAttribute('aria-expanded', String(!isOpen));
            thinkingToggle.textContent = isOpen
              ? uiText('showThinking', msg.languageCode || chat.lastAnswerLanguage || 'en-IN')
              : uiText('hideThinking', msg.languageCode || chat.lastAnswerLanguage || 'en-IN');
          });
        }

        const isMostRecentBot = !!latestBotMessage && latestBotMessage.ts === msg.ts;
        actions.appendChild(createSpeakerButton(chat, msg, isMostRecentBot));
        head.appendChild(actions);
        div.appendChild(head);
      }

      const body = document.createElement('div');
      if (msg.type === 'bot') {
        const parsed = parseAssistantResponse(msg.text);
        body.appendChild(buildFormattedAnswerNode(parsed.answer));
        const refsNode = buildReferencesNode(msg.sources, msg.languageCode || chat.lastAnswerLanguage || 'en-IN');
        if (refsNode) {
          body.appendChild(refsNode);
        }
        const followupNode = buildFollowUpOptionsNode(msg);
        if (followupNode) {
          body.appendChild(followupNode);
        }
        const feedbackRow = buildFeedbackRow(chat, msg);
        if (feedbackRow) {
          body.appendChild(feedbackRow);
        }
        if (msg.feedbackFormOpen) {
          body.appendChild(buildFeedbackForm(chat, msg));
        }
      } else {
        body.textContent = msg.text;
      }
      div.appendChild(body);
      messages.appendChild(div);
    });
    messages.scrollTop = messages.scrollHeight;
  }

  debug.textContent = chat.lastResponse ? JSON.stringify(chat.lastResponse, null, 2) : 'No calls yet.';
}

function renderAll() {
  renderChatList();
  renderMessages();
}

function appendMessage(text, type = 'bot', options = {}) {
  const chat = getActiveChat();
  if (!chat) return;
  chat.messages.push({
    text,
    type,
    ts: nowIso(),
    languageCode: options.languageCode || null,
    sources: normalizeSources(options.sources),
    feedbackToken: options.feedbackToken || null,
    originalQuestion: options.originalQuestion || null,
    feedbackSubmitted: !!options.feedbackSubmitted,
    feedbackKind: options.feedbackKind || null,
    feedbackFormOpen: false,
    followUpOptions: Array.isArray(options.followUpOptions) ? options.followUpOptions : [],
    audioBase64: options.audioBase64 || null,
    audioStatus: options.audioStatus || null,
    audioMimeType: options.audioMimeType || null,
  });
  chat.updatedAt = nowIso();
  saveChats();
  renderAll();
}

function beginNewChat() {
  const chat = createChat();
  state.chats.unshift(chat);
  state.activeChatId = chat.id;
  saveChats();
  renderAll();
}

function deleteActiveChat() {
  if (state.chats.length === 1) {
    const only = state.chats[0];
    only.messages = [];
    only.title = 'New Conversation';
    only.lastQuestion = null;
    only.lastAnswer = null;
    only.lastFeedbackToken = null;
    only.lastResponse = null;
    only.lastAnswerLanguage = 'en-IN';
    only.updatedAt = nowIso();
    saveChats();
    renderAll();
    return;
  }

  const current = getActiveChat();
  if (!current) return;

  const ok = window.confirm(uiText('deleteConfirm', current.lastAnswerLanguage || 'en-IN'));
  if (!ok) return;

  state.chats = state.chats.filter((c) => c.id !== current.id);
  state.activeChatId = state.chats[0].id;
  saveChats();
  renderAll();
}

async function sendMessage(sourceText = null, options = {}) {
  const chat = getActiveChat();
  if (!chat) return;

  const apiBase = getApiBase();
  const channel = document.getElementById('channelSelect').value;
  const locationHint = document.getElementById('locationHint').value.trim() || null;
  const input = document.getElementById('messageInput');
  const message = (sourceText ?? input.value).trim();
  if (!message) return;

  appendMessage(message, 'user');
  input.value = '';

  chat.lastQuestion = message;
  if (chat.title === 'New Conversation') {
    chat.title = shortTitle(message);
  }

  let url = `${apiBase}/chat`;
  let payload = {
    message,
    channel,
    session_id: chat.id,
    language_code: options.forceLanguageCode || null,
    location_hint: locationHint,
  };

  if (channel === 'whatsapp') {
    url = `${apiBase}/whatsapp/webhook`;
    payload = { from_number: '+919999999999', message, name: 'Citizen Demo' };
  }

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Request failed with ${response.status}`);
    }

    const data = await response.json();
    const answer = channel === 'whatsapp' ? data.reply : data.answer;
    const responseLanguage = channel === 'whatsapp'
      ? data?.meta?.detected_language || 'en-IN'
      : data.language_code || data.detected_language || 'en-IN';

    appendMessage(answer, 'bot', {
      languageCode: responseLanguage,
      sources: data.sources || [],
      feedbackToken: data.feedback_token || null,
      originalQuestion: message,
      followUpOptions: data.follow_up_options || [],
      audioBase64: data.audio_base64 || null,
      audioStatus: data.audio_status || null,
      audioMimeType: data.audio_mime_type || null,
    });
    chat.lastAnswer = answer;
    chat.lastAnswerLanguage = responseLanguage;
    chat.lastFeedbackToken = data.feedback_token || 'whatsapp-mock-token';
    chat.lastResponse = data;
    chat.updatedAt = nowIso();
    saveChats();
    renderAll();

    const parsed = parseAssistantResponse(answer);
    const played = data.audio_status === 'ok' && playAudioBase64(data.audio_base64 || null, data.audio_mime_type || null);
    if (!played) {
      speakText(parsed.answer, responseLanguage);
    }
  } catch (err) {
    appendMessage(`${uiText('apiUnreachable', chat.lastAnswerLanguage || 'en-IN')} ${err.message}`, 'bot', { languageCode: chat.lastAnswerLanguage || 'en-IN' });
  }
}

async function generateVoiceStub() {
  const chat = getActiveChat();
  if (!chat?.lastAnswer) {
    appendMessage(uiText('askFirstTts', 'en-IN'), 'bot', { languageCode: 'en-IN' });
    return;
  }

  const apiBase = getApiBase();

  try {
    const response = await fetch(`${apiBase}/voice/tts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: chat.lastAnswer, language_code: chat.lastAnswerLanguage || 'en-IN' }),
    });

    if (!response.ok) {
      throw new Error(`TTS failed with ${response.status}`);
    }

    const data = await response.json();
    appendMessage(`${uiText('voiceStatus', chat.lastAnswerLanguage || 'en-IN')}: ${data.detail}`, 'bot', { languageCode: chat.lastAnswerLanguage || 'en-IN' });
  } catch (err) {
    appendMessage(`${uiText('voiceFailed', chat.lastAnswerLanguage || 'en-IN')} ${err.message}`, 'bot', { languageCode: chat.lastAnswerLanguage || 'en-IN' });
  }
}

function setupVoiceSupport() {
  if ('speechSynthesis' in window) {
    const updateVoices = () => {
      state.voices = window.speechSynthesis.getVoices();
      renderAll();
    };
    updateVoices();
    window.speechSynthesis.onvoiceschanged = updateVoices;
  }

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const micBtn = document.getElementById('micBtn');

  if (!SpeechRecognition) {
    micBtn.disabled = true;
    micBtn.title = uiText('voiceUnavailable', 'en-IN');
    return;
  }

  state.recognition = new SpeechRecognition();
  state.recognition.continuous = true;
  state.recognition.interimResults = true;
  state.recognition.maxAlternatives = 1;

  state.recognition.onstart = () => {
    const lang = getActiveChat()?.lastAnswerLanguage || getPreferredRecognitionLanguage();
    state.isRecording = true;
    micBtn.classList.add('recording');
    micBtn.setAttribute('aria-label', uiText('stopVoice', lang));
    micBtn.title = uiText('stopVoice', lang);
  };

  state.recognition.onend = () => {
    const lang = getActiveChat()?.lastAnswerLanguage || 'en-IN';
    state.isRecording = false;
    micBtn.classList.remove('recording');
    micBtn.setAttribute('aria-label', uiText('startVoice', lang));
    micBtn.title = uiText('startVoice', lang);
  };

  state.recognition.onerror = (event) => {
    const lang = getActiveChat()?.lastAnswerLanguage || 'en-IN';
    appendMessage(`${uiText('voiceError', lang)}: ${event.error}`, 'bot', { languageCode: lang });
  };

  state.recognition.onresult = async (event) => {
    let finalCombined = '';
    let interim = '';

    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const t = event.results[i][0].transcript || '';
      if (event.results[i].isFinal) {
        finalCombined += `${t} `;
      } else {
        interim += `${t} `;
      }
    }

    const input = document.getElementById('messageInput');
    const composed = `${finalCombined}${interim}`.trim();
    if (composed) input.value = composed;

    const finalTranscript = finalCombined.trim();
    if (!finalTranscript) return;

    const chat = getActiveChat();
    const inferredLanguage = detectSpeechLanguageCode(finalTranscript, chat?.lastAnswerLanguage || getPreferredRecognitionLanguage());
    const apiBase = getApiBase();

    try {
      await fetch(`${apiBase}/voice/stt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transcript_hint: finalTranscript.trim(), language_code: inferredLanguage }),
      });
    } catch (_err) {
      // best-effort backend hook
    }

    state.recognition.stop();
    await sendMessage(finalTranscript, { forceLanguageCode: inferredLanguage });
  };

  micBtn.addEventListener('click', () => {
    if (!state.recognition) return;
    if (state.isRecording) {
      state.recognition.stop();
      return;
    }

    const chat = getActiveChat();
    const lang = normalizeLangForSpeech(chat?.lastAnswerLanguage || getPreferredRecognitionLanguage());
    state.recognition.lang = lang;
    state.recognition.start();
  });
}

function updateChannelTheme() {
  const channel = document.getElementById('channelSelect').value;
  const frame = document.querySelector('.phone-frame');
  const header = document.querySelector('.phone-header');
  if (!frame || !header) return;
  frame.setAttribute('data-channel', channel);
  header.textContent = channel === 'whatsapp' ? 'WhatsApp' : 'Conversation';
}

function wireEvents() {
  document.getElementById('sendBtn').addEventListener('click', () => sendMessage());
  document.getElementById('ttsBtn').addEventListener('click', generateVoiceStub);
  document.getElementById('newChatBtn').addEventListener('click', beginNewChat);
  document.getElementById('deleteChatBtn').addEventListener('click', deleteActiveChat);
  document.getElementById('apiBase').addEventListener('change', getApiBase);
  document.getElementById('apiBase').addEventListener('blur', getApiBase);
  document.querySelectorAll('.quick-chip').forEach((btn) => {
    btn.addEventListener('click', () => {
      const prompt = btn.getAttribute('data-prompt') || '';
      if (!prompt) return;
      sendMessage(prompt);
    });
  });
  document.getElementById('messageInput').addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });
  document.getElementById('channelSelect').addEventListener('change', updateChannelTheme);
}

function init() {
  initializeApiBaseInput();
  loadChats();
  wireEvents();
  setupVoiceSupport();
  updateChannelTheme();
  renderAll();
}

init();
