# AGENTS.md

## Cursor Cloud specific instructions

This repository ("dynamics") contains dynamics usage samples. It includes a browser-based **Ship Battle** game (`index.html`, `style.css`, `game.js`) and a Terraform-oriented `.gitignore`.

### Repository state

- **Ship Battle game** — pure HTML/CSS/JavaScript, no build step required.
- The `.gitignore` is configured for **Terraform** (`.terraform/`, `*.tfstate`, `*.tfvars`, etc.).
- **No package manager, no dependencies, no build system, no test framework** is present.

### Development notes

#### Running the game locally
Serve the repo root with any static HTTP server, e.g.:
```
python3 -m http.server 8765
```
Then open `http://localhost:8765/index.html` in a browser.

#### Testing
- No automated tests exist; test manually in the browser.
- Open the browser console to check for JS errors.
- Verify: ship placement (manual & random), battle phase, hit/miss visuals, score updates, game-over overlay.

#### Linting
No lint configuration is present. Standard browser DevTools console is sufficient.
