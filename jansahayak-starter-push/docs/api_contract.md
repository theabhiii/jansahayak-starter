# API Contract

## POST /chat
Request:
```json
{
  "message": "I am from Patna, Bihar. Which schemes can help farmers?",
  "channel": "web",
  "session_id": "demo-1",
  "language_code": "en-IN",
  "location_hint": "800001"
}
```

## POST /chat/feedback
Request:
```json
{
  "session_id": "demo-1",
  "feedback_token": "uuid",
  "original_question": "I am from Patna, Bihar. Which schemes can help farmers?",
  "original_answer": "...",
  "feedback": "negative",
  "reason": "Need simpler and more location-specific answer"
}
```

## POST /voice/tts
Request:
```json
{
  "text": "Welcome to JanSahayak",
  "language_code": "en-IN"
}
```

## POST /whatsapp/webhook
Request:
```json
{
  "from_number": "+919999999999",
  "message": "मेरा जिला पुणे है। महिलाओं के लिए कौन सी योजनाएं हैं?",
  "name": "Citizen Demo"
}
```
