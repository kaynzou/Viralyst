# Deploying Viralyst

The website goes on **Vercel** and the API on **Render**. Both are free and need no credit card. The
first time takes about 20 minutes; after that, every `git push` updates the live site by itself.

```
GitHub ── push ──▶ Vercel builds frontend/              → https://viralyst-xxxx.vercel.app
   │
   └──── push ──▶ Render builds backend/Dockerfile      → https://viralyst-api.onrender.com
```

> **Why not Hugging Face?** This guide first used Hugging Face Spaces. In 2026 Hugging Face started
> charging for the Docker (and Gradio) Spaces an API needs, so we moved the API to Render. Because the
> API is a container, only these instructions and one line of the Dockerfile changed.

## Before you start

Make your **access code**, the password that unlocks AI features on the live site. Run this in your
own Terminal (not in a chat) and save the result in a password manager or Notes:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(18))"
```

## Step 1: Put the API on Render

1. Go to [render.com](https://render.com) and sign up with your **GitHub** account.
2. Click **New +**, then **Web Service**, then connect GitHub. When GitHub asks which repositories
   Render may see, choose **Only select repositories** and pick **kaynzou/Viralyst**.
3. Fill in the form:
   - **Name:** `viralyst-api` (this becomes the address, e.g. `https://viralyst-api.onrender.com`)
   - **Branch:** `main`
   - **Root Directory:** `backend`
   - **Language / Runtime:** **Docker** (Render finds `backend/Dockerfile`)
   - **Instance Type:** **Free**
4. Under **Environment Variables**, add:
   - `VIRALYST_ACCESS_CODE`: your access code
   - `VIRALYST_DAILY_BUDGET`: the most AI may cost per day, in dollars. It must cover one full run on
     the model you'll use: about `6` for Opus, `3` for Sonnet, `1` for Haiku.
   - `ANTHROPIC_API_KEY`: your Claude key, whenever you have it. Until then, the live site is the free simulator.
5. Under **Advanced**, set **Health Check Path** to `/api/status`. Leave **Auto-Deploy** on.
6. Click **Create Web Service** and watch the build log. The first build takes 5–10 minutes
   (Python libraries, ffmpeg, the Whisper model). It's done when the log says the service is live.
7. Check it: open `https://<your-service>.onrender.com/api/status`. You should see some JSON.

## Step 2: Put the website on Vercel

1. Go to [vercel.com](https://vercel.com) and sign up with your **GitHub** account.
2. Click **Add New**, then **Project**, and import **kaynzou/Viralyst**.
3. Set **Root Directory** to `frontend`. Vercel detects Next.js by itself.
4. Under **Environment Variables**, add `NEXT_PUBLIC_API_URL` = your Render address,
   e.g. `https://viralyst-api.onrender.com` (no slash at the end).
5. Click **Deploy**. You get an address like `https://viralyst-xxxx.vercel.app`.

## Step 3: Let the website talk to the API

1. On Render, open your service, go to **Environment**, and add `VIRALYST_ALLOWED_ORIGINS` = your Vercel
   address (no slash at the end). For several addresses, separate them with commas.
2. Click **Save, rebuild, and deploy** (or **Save and deploy**).
3. Open your Vercel address. After "Waking up the Viralyst server…" you should see "API connected".
   Run a simulation!

## Step 4: Safety nets for your money

- In the **Anthropic Console**, set a monthly **spend limit**. The daily budget resets whenever the
  server restarts or sleeps, so the Console limit is your real backstop.
- Keep the access code secret. To change it, edit `VIRALYST_ACCESS_CODE` on Render and redeploy.

## Everyday use

- **Updating:** push to GitHub. Vercel rebuilds the website and Render rebuilds the API, both by themselves.
- **Using AI on the live site:** open the settings, enter the access code and click **Unlock**. It's
  remembered in that browser until you click **Lock**.
- **Undoing a bad change:** `git revert <commit>` then `git push`, and both sides redeploy the old version.
  Render can also roll back to an earlier deploy from its **Events** page.

## Good to know about the free plans

- Render's free API **sleeps after 15 minutes** without visitors. The next visitor waits about a minute;
  the website shows "Waking up the Viralyst server…" and keeps trying by itself.
- Render gives **750 free hours a month**. Sleeping time doesn't count, so one API fits comfortably.
- The API's disk is **temporary**: uploaded videos disappear on restart, redeploy or sleep.
- The free instance is small. The simulator runs fine; analyzing uploaded videos (Whisper) may be slow.
  If it struggles, analyze videos on your computer with `analyze_video.py` instead, or upgrade the instance.
- Vercel's free Hobby plan is for personal, non-commercial projects.

## Troubleshooting

| What you see | Likely cause | What to do |
|---|---|---|
| "Waking up the Viralyst server…" for more than 2 minutes, then "Can't reach the Viralyst API" | The API is still building, failed to build, or `NEXT_PUBLIC_API_URL` is wrong | Open `/api/status` on Render directly. Fix the variable in Vercel, then **Redeploy** (this variable is baked in when the site is built). |
| `/api/status` works, but the website can't reach it | Step 3 isn't done, or the address doesn't match exactly | Check `VIRALYST_ALLOWED_ORIGINS` matches your Vercel address exactly (`https://`, no slash at the end). |
| The Render build fails | Something went wrong while building the container | Read the build log from the bottom up and look for the first error. |
| "Today's AI budget is used up" right away | The budget is smaller than one full run | Raise `VIRALYST_DAILY_BUDGET`, or use a cheaper model. |
| "AI features on this site need the access code" | Not unlocked in this browser | Enter the code in the settings. |
