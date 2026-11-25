# Family Locator

A small, **consent-based** live-location web app for family and friends. Everyone
shares *their own* location on purpose — there's no way to look up a stranger, a
phone number, or a social-media account. That's deliberate.

## What it does

- Each person opens the page, enters their name and a shared **circle code**.
- They tap **Start sharing** and allow their browser's location prompt.
- Everyone using the same code sees each other live on a map, with name and
  "last updated" time.
- Tapping **Stop sharing**, closing the tab, or leaving removes them from the map.

## How it respects privacy

- **Opt-in only.** No one appears until they tap *Start sharing* and allow
  location on their own device. The browser enforces that prompt — the app
  cannot bypass it.
- **Scoped to a circle.** You only see people who typed the exact same code, so
  pick a code and share it privately (e.g. in your family WhatsApp group).
- **Live, not logged.** Positions are overwritten, not kept as a history trail.
- **Easy to leave.** Stop sharing at any time; you disappear from everyone's map.

> This app does **not** and **cannot** locate someone from a phone number or a
> TikTok/Instagram username. Those aren't technically possible from a web page,
> and tracking someone without their consent would be stalking. This is the
> legitimate, consent-first version.

## Try it right now (demo mode)

Open `index.html` through a local server (geolocation needs `https://` or
`localhost`):

```bash
cd family-locator
python3 -m http.server 8000
# then visit http://localhost:8000
```

Out of the box it runs in **demo mode**: it syncs across browser tabs on the same
device, so you can see the whole flow. Open two tabs, join the same circle in
each, and watch them appear together.

## Real cross-phone sharing (free, ~5 min)

To let family on *different* phones see each other, add a free Firebase Realtime
Database:

1. Create a project at <https://console.firebase.google.com>.
2. **Build → Realtime Database → Create database** (start in test mode).
3. **Project settings → Your apps → Web** and copy the config values.
4. Paste them into `firebase-config.js` and uncomment that block.
5. In `index.html`, uncomment the two Firebase `<script>` lines (shown in
   `firebase-config.js`).

### Suggested database rules (replace test mode once it works)

```json
{
  "rules": {
    "circles": {
      "$circle": {
        "members": {
          ".read": true,
          "$uid": { ".write": true }
        }
      }
    }
  }
}
```

This lets anyone with a circle code read that circle and write only their own
entry. For a family app that's usually fine; for stronger control, add Firebase
Anonymous Auth and key writes to `auth.uid`.

## Host it (so phones can use it)

Any static host works. **GitHub Pages** is easiest:

1. Push this repo.
2. Repo **Settings → Pages →** deploy from your branch, folder `/family-locator`
   (or move these files to the repo root / `docs`).
3. Share the resulting `https://…` link with your circle.

HTTPS is required for live location on phones — GitHub Pages provides it.

## Files

| File | Purpose |
|------|---------|
| `index.html` | Markup: onboarding + map screen |
| `styles.css` | Light/dark themed styling |
| `app.js` | Geolocation, map, roster, pluggable sync backends |
| `firebase-config.js` | Optional real-time backend config |

Map tiles: OpenStreetMap. Map library: Leaflet.
