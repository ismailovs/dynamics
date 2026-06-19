# AGENTS.md

## Cursor Cloud specific instructions

This repository ("dynamics") contains dynamics usage samples. It includes a browser-based **Ship Battle** game (`index.html`, `style.css`, `game.js`), the **5WhyAI** root cause analysis app (`5whyai/`), and a Terraform-oriented `.gitignore`.

### Repository state

- **Ship Battle game** — pure HTML/CSS/JavaScript, no build step required.
- The `.gitignore` is configured for **Terraform** (`.terraform/`, `*.tfstate`, `*.tfvars`, etc.).
- **No package manager, no dependencies, no build system, no test framework** is present.

### Development notes

#### Running the game locally (single player)
Serve the repo root with any static HTTP server, e.g.:
```
python3 -m http.server 8765
```
Then open `http://localhost:8765/index.html` in a browser.

#### Running multiplayer (2-player over network)
1. Install Node dependencies once:
   ```
   npm install
   ```
2. Start the WebSocket relay server:
   ```
   node server.js          # listens on ws://localhost:3000
   PORT=4000 node server.js  # custom port
   ```
3. Serve the frontend as above.
4. Player 1 opens the game → Multiplayer → Create Room → shares the 4-char code.
5. Player 2 opens the game → Multiplayer → enters code → Join.
6. Both place ships → click Ready → battle begins.

For internet play, deploy `server.js` to a public host (e.g. Render, Railway, Fly.io).
Then players open: `http://<host>/index.html?server=wss://<ws-host>:<port>`

#### Testing
- No automated tests exist; test manually in the browser.
- Open the browser console to check for JS errors.
- Verify: ship placement (manual & random), battle phase, hit/miss visuals, score updates, game-over overlay.
- For multiplayer: open two browser tabs, create a room in one, join from the other.

#### Linting
No lint configuration is present. Standard browser DevTools console is sufficient.

---

## 5WhyAI App (`5whyai/`)

A professional AI-powered root cause analysis tool based on the 5 Whys method.

### Stack
- **Frontend**: React 18 + Vite (port 5173)
- **Backend**: Express.js (port 3001) with OpenAI integration
- **Storage**: `localStorage` for analysis history (no database required)

### Running locally

1. Install dependencies:
   ```
   cd 5whyai && npm install
   ```
2. Copy and configure `.env`:
   ```
   cp .env.example .env
   # Add OPENAI_API_KEY if you have one (optional — app works without it using structured fallback answers)
   ```
3. Start backend:
   ```
   node server/index.js
   ```
4. Start frontend (separate terminal):
   ```
   npm run client
   ```
5. Open `http://localhost:5173`

Or start both together:
```
npm run dev
```

### Testing
- Test manually in browser: go through Welcome → Business Issue → enter problem → complete 5 Whys → view Short + Full Conclusion
- API endpoints can be tested directly:
  - `POST http://localhost:3001/api/next-why` — get next Why question + 5 answers
  - `POST http://localhost:3001/api/conclusion` — generate full conclusion
- Without an OpenAI key, structured fallback answers are used automatically
- Check browser DevTools console for JS errors
