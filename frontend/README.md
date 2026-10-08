# Viralyst frontend

The website: a Next.js app that talks to the Python API in `../backend`.
The easiest way to start both is `./dev.sh` from the project folder.

```bash
npm install      # once
npm run dev      # http://localhost:3000 (needs the API running on port 8000)
```

## What's where

| Path | What it does |
|---|---|
| `app/page.tsx` | The page (a Server Component that renders the Simulator) |
| `app/layout.tsx` | The HTML around every page: title, fonts |
| `app/globals.css` | Colors for light and dark mode, and the dot animation |
| `components/Simulator.tsx` | The interactive part: settings, running a simulation, shareable links |
| `components/Cascade.tsx` | The four waves, one dot per simulated viewer, and each wave's score |
| `components/PersonaCard.tsx` | Details of the viewer you clicked |
| `components/Report.tsx` | Verdict, signals, who engaged, comments, AI cost |
| `components/OddsPanel.tsx` | 200 free simulations and how often each outcome happens |
| `components/UploadPanel.tsx` | Upload your own video for analysis (needs an API key) |
| `components/ComparePanel.tsx` | A/B test two videos |
| `components/AccessCode.tsx` | Unlock AI features on the live site with your access code |
| `lib/api.ts` | Every call to the Python API, including the live stream |
| `lib/types.ts` | The shapes of the data the API sends |

## Checks

```bash
npx tsc --noEmit   # types
npm run lint       # code style and common mistakes
npm run build      # a full production build
```

The API address defaults to `http://localhost:8000`. Set `NEXT_PUBLIC_API_URL` to change it (on Vercel,
see `../deploy/README.md`). It's built into the site, so redeploy after changing it.
