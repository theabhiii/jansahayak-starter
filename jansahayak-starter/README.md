# JanSahayak

AI-powered unified multilingual, location-aware citizen service assistant with web chat, voice hooks, and WhatsApp-style interaction.

## Assumptions
- This repository is intended for hackathon/demo and developer onboarding use, not production deployment.
- No real government transactional systems are connected; APIs for eligibility/grievance/status are mocked.
- Sarvam API features depend on valid credentials and package availability at runtime.

## 1. Overview
JanSahayak provides a single conversational interface for discovering schemes, checking basic eligibility context, and routing grievances with location awareness.

### Key features
- Multichannel interaction: web chat, WhatsApp-style webhook, voice STT/TTS hooks.
- Multilingual flow with language detection, session language consistency, and response translation layer.
- Location-aware responses (state/district/pincode resolver).
- Knowledge retrieval over local scheme data (`schemes.json`).
- Feedback loop (`helpful/not helpful`) with answer simplification/retry.
- Debug-friendly response metadata (`language_trace`, sources, actions).

## 2. Architecture & Design
### Components
- `apps/web`: static UI (chat sessions, voice UX, metadata panel).
- `apps/api/app/routes`: API endpoints (`/chat`, `/voice`, `/whatsapp`).
- `apps/api/app/services/orchestrator.py`: request lifecycle orchestration.
- `apps/api/app/services/sarvam_service.py`: translation/STT/TTS integrations and fallbacks.
- `apps/api/app/services/knowledge_base.py`: local search over schemes.
- `apps/api/app/services/mock_services.py`: eligibility/grievance mocked integrations.
- `apps/api/app/utils/language.py`: detection + normalization.
- `apps/api/app/utils/location.py`: location extraction.

### Request lifecycle (chat)
1. Client sends message to `POST /chat`.
2. Orchestrator detects language and resolves session language.
3. Location resolver extracts pincode/state/district.
4. Knowledge + mock services generate contextual draft answer.
5. Response generation is invoked with explicit language parameters.
6. Final translation layer enforces output in session language.
7. API returns answer + metadata (`language_trace`, sources, actions).

### External integrations
- Sarvam AI SDK / REST translation endpoint (`/translate`).
- Optional future: real government scheme/status/grievance systems.

## 3. Prerequisites
- Python `3.11+` (tested with Python 3.12 in this workspace).
- `pip` and virtual environment support.
- Sarvam subscription key for live translation/TTS/STT.
- Browser with modern JS support for web UI.

## 4. Installation & Setup
### 4.1 Clone and prepare environment
```bash
cd jansahayak-starter
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS/Linux
# source .venv/bin/activate
pip install -r requirements.txt
```

### 4.2 Configure environment variables
```bash
# Windows PowerShell
Copy-Item .env.example .env
# macOS/Linux
# cp .env.example .env
```

Edit `.env`:
```env
APP_ENV=local
APP_NAME=JanSahayak API
DEBUG=true
SARVAM_API_KEY=<your-key>
SARVAM_BASE_URL=https://api.sarvam.ai
SARVAM_TRANSLATE_MODEL=mayura:v1
SARVAM_TRANSLATE_MODE=formal
SARVAM_SPEAKER_GENDER=Male
SARVAM_ENABLE_PREPROCESSING=false
SARVAM_NUMERALS_FORMAT=native
DEFAULT_LANGUAGE=en-IN
DEFAULT_STATE=Delhi
DEFAULT_DISTRICT=New Delhi
```

### 4.3 Start backend
```bash
uvicorn apps.api.app.main:app --reload --port 8000
```

### 4.4 Start frontend
```bash
python -m http.server 5500 -d apps/web
```

Open:
- Web UI: `http://localhost:5500`
- API docs (Swagger): `http://localhost:8000/docs`

## 5. Usage
### Run the application
1. Start backend.
2. Start frontend static server.
3. Open browser and send messages via web chat.

### Example prompts
- `I am from Patna, Bihar. Which schemes can help farmers?`
- `मेरा जिला पुणे है। महिलाओं के लिए कौन सी योजनाएं हैं?`
- `I need grievance help for ration card delay in Bhopal.`

### Sample output (shape)
```json
{
  "session_id": "session-123",
  "session_language": "hi-IN",
  "language_code": "hi-IN",
  "detected_language": "hi-IN",
  "detection_confidence": 0.91,
  "location": {"pincode": null, "state": "Delhi", "district": "New Delhi"},
  "answer": "...",
  "sources": [{"id": "sch-1", "title": "PM-KISAN", "url": "..."}],
  "actions": ["scheme_discovery", "eligibility_check", "grievance_routing"],
  "feedback_token": "uuid",
  "language_trace": {
    "detected_language": "hi-IN",
    "sent_response_language": "hi-IN",
    "received_language": "en-IN",
    "mismatch_detected": false,
    "translation_payload": {"target_language": "hi-IN"}
  }
}
```

## 6. API Documentation
### `GET /`
Health endpoint.

Response:
```json
{"status": "ok", "app": "JanSahayak API", "env": "local"}
```

### `POST /chat`
Primary chat endpoint.

Request:
```json
{
  "message": "I am from Patna, Bihar. Which schemes can help farmers?",
  "channel": "web",
  "session_id": "demo-1",
  "language_code": null,
  "location_hint": "800001"
}
```

### `POST /chat/feedback`
Retry/improve prior answer.

Request:
```json
{
  "session_id": "demo-1",
  "feedback_token": "uuid",
  "original_question": "...",
  "original_answer": "...",
  "feedback": "negative",
  "reason": "Need simpler response",
  "language_code": "hi-IN"
}
```

### `POST /voice/tts`
Text-to-speech hook.

### `POST /voice/stt`
Speech-to-text hook (currently transcript-hint friendly).

### `POST /whatsapp/webhook`
WhatsApp-style mock inbound webhook.

Request:
```json
{
  "from_number": "+919999999999",
  "message": "मुझे योजना जानकारी चाहिए",
  "name": "Citizen Demo"
}
```

### Error handling
- Validation errors: FastAPI/Pydantic 422 responses.
- Upstream translation issues: logged warnings, fallback behavior.
- API transport failures: surfaced as backend errors and logged.

## 7. Configuration & Customization
Key configurable settings:
- App: `APP_ENV`, `APP_NAME`, `DEBUG`
- Defaults: `DEFAULT_LANGUAGE`, `DEFAULT_STATE`, `DEFAULT_DISTRICT`
- Sarvam: `SARVAM_*` translation and integration settings

Customization points:
- Extend supported language heuristics in `utils/language.py`.
- Add schemes in `apps/api/app/data/schemes.json`.
- Replace mock services with real adapters in `services/mock_services.py`.

## 8. Localization / Language Handling
- Language is detected per message.
- Session language is persisted and used for consistency.
- Clear language switch is supported when detection confidence is high.
- Final response always passes through translation layer into session language.
- Supported examples include English (`en-IN`), Hindi (`hi-IN`), Spanish (`es-ES`), and additional configured Indic codes.

## 9. Logging, Monitoring & Error Handling
### Logging strategy
- Global logging configured in `apps/api/app/main.py`.
- Orchestrator logs language trace (`detected`, `sent`, `received`, translation target).
- Sarvam service logs request payload metadata and translation failures.

### Monitoring recommendations
- Capture logs centrally (ELK/Datadog/CloudWatch in future).
- Add request IDs and latency metrics in middleware.

### Common issues
- `sarvamai` import errors: run `pip install -r requirements.txt`.
- Translation not applied: verify `SARVAM_API_KEY` and `SARVAM_BASE_URL`.
- Mixed-language outputs: inspect `language_trace.translation_payload` in response.

## 10. Security Considerations
- Current state: no authentication/authorization on API endpoints.
- CORS is open (`*`) for demo convenience.
- Do not commit real secrets; keep `.env` local.
- Avoid sending PII in demo prompts.
- For production: add auth, RBAC, encrypted secrets, rate limits, audit logs.

## 11. Testing
### Current status
- No formal automated test suite is included in this starter.

### Suggested checks
- Syntax check:
```bash
python -c "import ast, pathlib; [ast.parse(pathlib.Path(f).read_text(encoding='utf-8')) for f in pathlib.Path('apps').rglob('*.py')]"
```
- Manual API smoke tests via Swagger (`/docs`) or curl.

### Recommended future test coverage
- Language detection/session locking tests.
- Translation layer contract tests.
- Endpoint integration tests with mocked Sarvam responses.
- Frontend behavior tests (chat sessions, voice controls).

## 12. Limitations & Known Issues
- Government APIs are mocked (non-production data/flows).
- Translation quality depends on upstream service availability and model behavior.
- Voice endpoints are scaffolded and may return mocked fallback content.
- No persistent database for conversations/analytics.
- No auth/rate limiting/tenant isolation.

## 13. Future Enhancements
- Real government integration adapters.
- Persistent datastore for chats/feedback/analytics.
- Vector DB + ingestion pipeline for richer RAG.
- Full WhatsApp Business API integration.
- Observability: metrics/traces/dashboard.
- Production hardening (auth, RBAC, throttling, PII policy).

## 14. Contribution Guidelines
### Coding standards
- Python: clear module boundaries, type hints where practical.
- Frontend JS/CSS: keep UI behavior and accessibility aligned.
- Prefer small, reviewable commits.

### Pull request workflow
1. Create feature branch.
2. Implement and self-test locally.
3. Update docs/examples when behavior changes.
4. Open PR with summary, test steps, and screenshots for UI changes.

## 15. License & Ownership
- License: **Not explicitly declared in this repository** (assumption).
- Ownership: Project contributors/team listed in project materials.

If you want a specific license (`MIT`, `Apache-2.0`, etc.), add a `LICENSE` file and update this section.
