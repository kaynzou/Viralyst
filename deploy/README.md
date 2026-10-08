# Deploying Viralyst

The website goes on **Vercel** and the API on **Hugging Face Spaces**. Both are free. The first
time takes about 20 minutes; after that, every `git push` updates the live site by itself.

```
GitHub ── push ──▶ Vercel builds frontend/        → https://viralyst-xxxx.vercel.app
   │
   └── GitHub Action ──▶ Hugging Face builds backend/Dockerfile → https://<you>-viralyst-api.hf.space
```

## Before you start

Make your **access code**, the password that unlocks AI features on the live site. Run this and
keep the result in a password manager:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(18))"
```

## Step 1: Create the Space on Hugging Face

1. Sign up at [huggingface.co](https://huggingface.co).
2. Click **New Space**:
   - **Space name:** `viralyst-api`
   - **SDK:** Docker, then **Blank**
   - **Hardware:** CPU basic (free)
   - **Visibility:** Public. Your code is already public on GitHub, and secrets stay hidden.
3. Open the Space's **Settings**, find **Variables and secrets**, and add:
   - **Secret** `VIRALYST_ACCESS_CODE`: your access code.
   - **Variable** `VIRALYST_DAILY_BUDGET`: the most AI may cost per day, in dollars. It must cover one
     full run on the model you'll use: about `6` for Opus, `3` for Sonnet, `1` for Haiku.
   - **Secret** `ANTHROPIC_API_KEY`: your Claude key, whenever you have it. Until then, the live site
     is the free simulator.

## Step 2: Connect GitHub to the Space

1. On Hugging Face, go to **Settings**, then **Access Tokens**, then **Create new token**. Choose type
   **Write** and copy the token.
2. On GitHub, open **kaynzou/Viralyst**, then **Settings**, then **Secrets and variables**, then **Actions**:
   - **Secrets** tab, **New repository secret:** name `HF_TOKEN`, value: the token.
   - **Variables** tab, **New repository variable:** name `HF_SPACE`, value: `<your-hf-username>/viralyst-api`.
3. On GitHub, go to **Actions**, open **Deploy API to Hugging Face**, and click **Run workflow**.
4. Watch the Space's **Logs** tab. The first build takes 5–10 minutes (Python libraries, ffmpeg,
   the Whisper model). Later builds are faster.
5. Check it: open `https://<your-hf-username>-viralyst-api.hf.space/api/status`. You should see some JSON.

## Step 3: Put the website on Vercel

1. Sign up at [vercel.com](https://vercel.com) with your GitHub account.
2. Click **Add New**, then **Project**, and import **kaynzou/Viralyst**.
3. Set **Root Directory** to `frontend`. Vercel detects Next.js by itself.
4. Under **Environment Variables**, add `NEXT_PUBLIC_API_URL` =
   `https://<your-hf-username>-viralyst-api.hf.space` (no slash at the end).
5. Click **Deploy**. You get an address like `https://viralyst-xxxx.vercel.app`.

## Step 4: Let the website talk to the API

1. In the Space's **Settings**, add the **variable** `VIRALYST_ALLOWED_ORIGINS` = your Vercel address
   (no slash at the end). For several addresses, separate them with commas.
2. The Space restarts with the new setting. If it doesn't, use **Factory reboot**.
3. Open your Vercel address. You should see "API connected". Run a simulation!

## Step 5: Safety nets for your money

- In the **Anthropic Console**, set a monthly **spend limit**. The daily budget resets whenever the Space
  restarts, so the Console limit is your real backstop.
- Keep the access code secret. To change it, edit the secret in the Space settings. The old code stops
  working when the Space restarts.

## Everyday use

- **Updating:** push to GitHub. Vercel rebuilds the website, and the Action redeploys the API if
  anything in `backend/` changed.
- **Using AI on the live site:** open the settings, enter the access code and click **Unlock**. It's
  remembered in that browser until you click **Lock**.
- **Undoing a bad change:** `git revert <commit>` then `git push`, and both sides redeploy the old version.

## Good to know about the free tiers

- The Space **sleeps** after about two days without visitors. The first visit after that takes a
  minute while it wakes up.
- Files uploaded to the Space are **temporary**: they disappear when it restarts.
- Vercel's free Hobby plan is for personal, non-commercial projects.

## Troubleshooting

| What you see | Likely cause | What to do |
|---|---|---|
| "Can't reach the Viralyst API" | Wrong `NEXT_PUBLIC_API_URL`, the Space is asleep or building, or step 4 isn't done | Open `/api/status` on the Space directly. Fix the variable in Vercel, then **Redeploy** (this variable is baked in when the site is built). |
| The Action says "Skipped" | `HF_SPACE` isn't set | Do step 2. |
| The Action fails at "Push to the Space" | The token is missing or read-only, or `HF_SPACE` is misspelled | Make a new **Write** token and check the name. |
| The Space says "Build error" | Something failed while building the container | Read the Space's **Logs** tab from the bottom up. |
| "Today's AI budget is used up" right away | The budget is smaller than one full run | Raise `VIRALYST_DAILY_BUDGET`, or use a cheaper model. |
| "AI features on this site need the access code" | Not unlocked in this browser | Enter the code in the settings. |
