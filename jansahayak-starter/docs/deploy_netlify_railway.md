# Deploy Guide: Netlify (Frontend) + Railway (Backend)

This setup gives you:
- `apps/web` hosted on Netlify with a stable HTTPS URL
- FastAPI backend hosted on Railway with a stable public API URL

## 1) Backend on Railway

1. Push this repository to GitHub.
2. In Railway, create a new project from the GitHub repo.
3. Set the project root to `jansahayak-starter` if Railway imports the outer folder.
4. Railway will use:
   - `requirements.txt`
   - `railway.toml`
   - `Procfile`
5. Add environment variables from your local `.env`.
   Recommended minimum:
   - `APP_ENV=prod`
   - `DEBUG=false`
   - `SARVAM_API_KEY=...`
   - any other keys you need from `.env.example`
6. Deploy and copy the Railway backend URL.
   Example:
   - `https://your-api.up.railway.app`
7. Verify it works:
   - `GET https://your-api.up.railway.app/`

## 2) Frontend on Netlify

1. Before deploying, open `apps/web/config.js`.
2. Set the Railway backend URL:

```js
window.JANSAHAYAK_CONFIG = window.JANSAHAYAK_CONFIG || {
  apiBaseUrl: 'https://your-api.up.railway.app',
};
```

3. Commit that change.
4. In Netlify, create a new site from your GitHub repo.
5. Use these settings:
   - Base directory: `jansahayak-starter`
   - Publish directory: `apps/web`
   - Build command: leave empty
6. Deploy.

## 3) How API URL Selection Works

The frontend now resolves the API base URL in this order:
1. `?apiBase=https://...` query parameter
2. Previously saved value from the sidebar field
3. `apps/web/config.js`
4. `http://localhost:8000` when running on localhost

This means:
- local development still works as before
- Netlify can use the Railway URL by default
- you can still override the backend from the UI without editing code

## 4) Smoke Test

1. Open the Netlify site.
2. Confirm the `API Base URL` field is already filled with the Railway URL.
3. Send a message in web chat.
4. Confirm `GET /` and `POST /chat` work.
5. Test voice and WhatsApp mock flow if needed.

## 5) Notes

- Netlify is only hosting the static frontend.
- Railway is the always-on public backend replacement for `ngrok`.
- Browser microphone features work better over HTTPS, so Netlify is a good fit for the frontend.
- Railway free plans may still sleep when idle depending on your plan.
