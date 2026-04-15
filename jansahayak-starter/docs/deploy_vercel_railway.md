# Deploy Guide: Vercel (Frontend) + Railway (Backend)

This guide deploys:
- `apps/web` on Vercel (free static hosting)
- FastAPI backend on Railway

## 1) Backend on Railway

1. Push your latest code to GitHub.
2. Go to Railway and click `New Project` -> `Deploy from GitHub repo`.
3. Select this repository.
4. Railway will detect Python and use:
   - `requirements.txt` for dependencies
   - `railway.toml` / `Procfile` for startup command
5. In Railway project settings, add environment variables from your local `.env`.
   Minimum recommended:
   - `APP_ENV=prod`
   - `DEBUG=false`
   - `SARVAM_API_KEY=...` (if using Sarvam APIs)
   - any other required app config keys from `.env.example`
6. After deploy, copy your backend URL, for example:
   - `https://your-api.up.railway.app`
7. Verify health:
   - `GET https://your-api.up.railway.app/`

## 2) Frontend on Vercel

1. Go to Vercel and click `Add New...` -> `Project`.
2. Import the same GitHub repository.
3. In project settings:
   - **Root Directory**: `apps/web`
   - **Framework Preset**: `Other`
   - **Build Command**: leave empty
   - **Output Directory**: leave empty
4. Deploy.
5. Open your Vercel URL.
6. In the app sidebar, set `API Base URL` to your Railway backend URL.
   - Example: `https://your-api.up.railway.app`

## 3) CORS and HTTPS Notes

- Frontend on Vercel is HTTPS by default.
- Browser mic input requires secure context (HTTPS or localhost).
- Backend currently allows CORS from all origins, so Vercel -> Railway should work.

## 4) Quick Smoke Test

1. Open Vercel app.
2. Set `API Base URL` to Railway URL.
3. Send a test message in chat.
4. Confirm response appears.
5. Test mic icon and TTS controls.

## 5) Free Tier Caveats

- Railway/Vercel free plans can have usage limits and sleep/idle behavior.
- First request after idle may be slower.
