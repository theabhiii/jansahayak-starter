const STORAGE_KEY = 'jansahayak_chats_v3';

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

function shortTitle(text) {
  const normalized = (text || '').replace(/\s+/g, ' ').trim();
  if (!normalized) return 'New Conversation';
  return normalized.length > 38 ? `${normalized.slice(0, 38)}...` : normalized;
}

function uiLanguage(code) {
  if (!code) return 'en';
  const normalized = String(code).toLowerCase();
  if (normalized.startsWith('hi')) return 'hi';
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
    },
    hi: {
      speakerAria: 'उत्तर सुनें',
      speakerTitle: 'उत्तर सुनें',
      speakerLatestOnly: 'केवल नवीनतम सहायक उत्तर चलाया जा सकता है',
      speakerUnsupported: 'उत्तर सुनें (इस भाषा के लिए उपलब्ध नहीं)',
      audioUnsupported: 'मौजूदा उत्तर भाषा के लिए ऑडियो प्लेबैक उपलब्ध नहीं है।',
      startPrompt: 'योजनाओं, पात्रता, शिकायत या स्थान-आधारित मार्गदर्शन के बारे में पूछना शुरू करें।',
      assistantLabel: 'सहायक',
      deleteConfirm: 'क्या आप इस चैट को स्थानीय इतिहास से स्थायी रूप से हटाना चाहते हैं?',
      apiUnreachable: 'API तक पहुंच नहीं हो पाई।',
      improveFirst: 'पहले एक संदेश भेजें, फिर Improve का उपयोग करें।',
      improveFailed: 'सुधार प्रक्रिया पूरी नहीं हो सकी।',
      askFirstTts: 'पहले कुछ पूछें ताकि मैं TTS के लिए पाठ भेज सकूं।',
      voiceStatus: 'आवाज़ स्थिति',
      voiceFailed: 'Voice कॉल विफल रहा।',
      voiceUnavailable: 'वॉयस इनपुट उपलब्ध नहीं',
      stopVoice: 'वॉयस इनपुट रोकें',
      startVoice: 'वॉयस इनपुट',
      voiceError: 'वॉयस इनपुट त्रुटि',
      thanks: 'धन्यवाद। आपकी प्रतिक्रिया गुणवत्ता सुधार के लिए दर्ज कर ली गई है।',
    },
    es: {
      speakerAria: 'Leer respuesta en voz alta',
      speakerTitle: 'Leer respuesta en voz alta',
      speakerLatestOnly: 'Solo se puede reproducir la respuesta más reciente del asistente',
      speakerUnsupported: 'Leer respuesta en voz alta (no compatible para este idioma)',
      audioUnsupported: 'La reproducción de audio no es compatible con el idioma de la respuesta actual.',
      startPrompt: 'Empieza preguntando por esquemas, elegibilidad, quejas o guía por ubicación.',
      assistantLabel: 'Asistente',
      deleteConfirm: '¿Eliminar este chat permanentemente del historial local?',
      apiUnreachable: 'No se pudo conectar con la API.',
      improveFirst: 'Primero envía un mensaje y luego usa Improve.',
      improveFailed: 'No se pudo completar la mejora.',
      askFirstTts: 'Primero pregunta algo para enviar texto a TTS.',
      voiceStatus: 'Estado de voz',
      voiceFailed: 'La llamada de voz falló.',
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

function normalizeLangForSpeech(code) {
  if (!code) return 'en-IN';
  return code;
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
    const ok = speakText(latest.text, latest.languageCode || languageCode);
    if (!ok) {
      appendMessage(uiText('audioUnsupported', languageCode), 'bot', { languageCode });
    }
  });
  return btn;
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
    const info = document.createElement('div');
    info.className = 'message bot';
    info.textContent = uiText('startPrompt', chat.lastAnswerLanguage || 'en-IN');
    messages.appendChild(info);
  } else {
    chat.messages.forEach((msg) => {
      const div = document.createElement('div');
      div.className = `message ${msg.type}`;

      if (msg.type === 'bot') {
        const head = document.createElement('div');
        head.className = 'message-head';

        const label = document.createElement('span');
        label.className = 'message-label';
        label.textContent = uiText('assistantLabel', msg.languageCode || chat.lastAnswerLanguage || 'en-IN');
        head.appendChild(label);

        const isMostRecentBot = !!latestBotMessage && latestBotMessage.ts === msg.ts;
        head.appendChild(createSpeakerButton(chat, msg, isMostRecentBot));
        div.appendChild(head);
      }

      const body = document.createElement('div');
      body.textContent = msg.text;
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

async function sendMessage(sourceText = null) {
  const chat = getActiveChat();
  if (!chat) return;

  const apiBase = document.getElementById('apiBase').value.trim();
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
    language_code: null,
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

    appendMessage(answer, 'bot', { languageCode: responseLanguage });
    chat.lastAnswer = answer;
    chat.lastAnswerLanguage = responseLanguage;
    chat.lastFeedbackToken = data.feedback_token || 'whatsapp-mock-token';
    chat.lastResponse = data;
    chat.updatedAt = nowIso();
    saveChats();
    renderAll();
  } catch (err) {
    appendMessage(`${uiText('apiUnreachable', chat.lastAnswerLanguage || 'en-IN')} ${err.message}`, 'bot', { languageCode: chat.lastAnswerLanguage || 'en-IN' });
  }
}

async function retryAnswer() {
  const chat = getActiveChat();
  if (!chat || !chat.lastQuestion || !chat.lastAnswer) {
    appendMessage(uiText('improveFirst', chat?.lastAnswerLanguage || 'en-IN'), 'bot', { languageCode: chat?.lastAnswerLanguage || 'en-IN' });
    return;
  }

  const apiBase = document.getElementById('apiBase').value.trim();

  try {
    const response = await fetch(`${apiBase}/chat/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: chat.id,
        feedback_token: chat.lastFeedbackToken,
        original_question: chat.lastQuestion,
        original_answer: chat.lastAnswer,
        feedback: 'negative',
        reason: 'Need a simpler and more location-specific answer',
        language_code: chat.lastAnswerLanguage || 'en-IN',
      }),
    });

    if (!response.ok) {
      throw new Error(`Feedback failed with ${response.status}`);
    }

    const data = await response.json();
    appendMessage(data.improved_answer, 'bot', { languageCode: chat.lastAnswerLanguage || 'en-IN' });
  } catch (err) {
    appendMessage(`${uiText('improveFailed', chat.lastAnswerLanguage || 'en-IN')} ${err.message}`, 'bot', { languageCode: chat.lastAnswerLanguage || 'en-IN' });
  }
}

async function generateVoiceStub() {
  const chat = getActiveChat();
  if (!chat?.lastAnswer) {
    appendMessage(uiText('askFirstTts', 'en-IN'), 'bot', { languageCode: 'en-IN' });
    return;
  }

  const apiBase = document.getElementById('apiBase').value.trim();

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
  state.recognition.continuous = false;
  state.recognition.interimResults = true;

  state.recognition.onstart = () => {
    const lang = getActiveChat()?.lastAnswerLanguage || 'en-IN';
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
    let interim = '';
    let finalTranscript = '';

    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const t = event.results[i][0].transcript || '';
      if (event.results[i].isFinal) {
        finalTranscript += t;
      } else {
        interim += t;
      }
    }

    const input = document.getElementById('messageInput');
    const composed = (finalTranscript || interim).trim();
    if (composed) input.value = composed;

    if (!finalTranscript.trim()) return;

    const chat = getActiveChat();
    const inferredLanguage = chat?.lastAnswerLanguage || 'en-IN';
    const apiBase = document.getElementById('apiBase').value.trim();

    try {
      await fetch(`${apiBase}/voice/stt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transcript_hint: finalTranscript.trim(), language_code: inferredLanguage }),
      });
    } catch (_err) {
      // best-effort backend hook
    }

    await sendMessage(finalTranscript.trim());
  };

  micBtn.addEventListener('click', () => {
    if (!state.recognition) return;
    if (state.isRecording) {
      state.recognition.stop();
      return;
    }

    const chat = getActiveChat();
    const lang = chat?.lastAnswerLanguage || 'en-IN';
    state.recognition.lang = normalizeLangForSpeech(lang);
    state.recognition.start();
  });
}

function wireEvents() {
  document.getElementById('sendBtn').addEventListener('click', () => sendMessage());
  document.getElementById('retryBtn').addEventListener('click', retryAnswer);
  document.getElementById('ttsBtn').addEventListener('click', generateVoiceStub);
  document.getElementById('helpfulBtn').addEventListener('click', () => {
    const lang = getActiveChat()?.lastAnswerLanguage || 'en-IN';
    appendMessage(uiText('thanks', lang), 'bot', { languageCode: lang });
  });
  document.getElementById('newChatBtn').addEventListener('click', beginNewChat);
  document.getElementById('deleteChatBtn').addEventListener('click', deleteActiveChat);
  document.getElementById('messageInput').addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });
}

function init() {
  loadChats();
  wireEvents();
  setupVoiceSupport();
  renderAll();
}

init();
