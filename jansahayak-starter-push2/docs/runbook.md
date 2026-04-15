# Runbook

## Commands in sequence

### Backend
```bash
cd jansahayak-starter
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn apps.api.app.main:app --reload --port 8000
```

### Frontend
Open a new terminal:
```bash
cd jansahayak-starter
python -m http.server 5500 -d apps/web
```

### Verify health
```bash
curl http://localhost:8000/
```

### Test chat
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I am from Patna, Bihar. Which schemes can help farmers?",
    "channel": "web",
    "session_id": "demo-1"
  }'
```

### Test Hindi chat
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "मेरा जिला पुणे है। महिलाओं के लिए कौन सी योजनाएं हैं?",
    "channel": "web",
    "session_id": "demo-2"
  }'
```

### Test feedback retry
```bash
curl -X POST http://localhost:8000/chat/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo-1",
    "feedback_token": "demo-token",
    "original_question": "I am from Patna, Bihar. Which schemes can help farmers?",
    "original_answer": "Sample answer",
    "feedback": "negative",
    "reason": "Need a simpler and more location-specific answer"
  }'
```

### Test WhatsApp mock
```bash
curl -X POST http://localhost:8000/whatsapp/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "from_number": "+919999999999",
    "message": "I am from Bhopal. I need help with ration card grievance.",
    "name": "Citizen Demo"
  }'
```

### Test voice stub
```bash
curl -X POST http://localhost:8000/voice/tts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Welcome to JanSahayak",
    "language_code": "en-IN"
  }'
```

## Demo sequence for presentation
1. Open web UI
2. Ask a location-aware scheme question
3. Show the answer and metadata panel
4. Click Not Helpful to trigger improved answer
5. Switch to WhatsApp mock and show the same flow
6. Trigger voice stub generation
