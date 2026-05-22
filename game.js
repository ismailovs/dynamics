/* =========================================================
   SHIP BATTLE — Complete Game Logic
   ========================================================= */

const GRID = 10;

const SHIPS_CONFIG = [
  { name: 'Carrier',    size: 5, icon: '🛳️' },
  { name: 'Battleship', size: 4, icon: '⚔️' },
  { name: 'Cruiser',    size: 3, icon: '🚢' },
  { name: 'Submarine',  size: 3, icon: '🤿' },
  { name: 'Destroyer',  size: 2, icon: '⚡' },
];

// Scoring
const SCORE = {
  HIT:       10,
  MISS:       0,
  SUNK_MULT: 20,   // × ship.size
  WIN_BONUS: 500,
};

/* =========================================================
   DATA STRUCTURES
   ========================================================= */

function makeGrid() {
  return Array.from({ length: GRID }, () =>
    Array.from({ length: GRID }, () => ({ ship: null, attacked: false }))
  );
}

function makeShip(cfg, id) {
  return {
    id,
    name: cfg.name,
    size: cfg.size,
    icon: cfg.icon,
    cells: [],   // [{r, c}]
    hits: 0,
    sunk: false,
  };
}

function placeShipOnGrid(grid, ship, r, c, horiz) {
  ship.cells = [];
  for (let i = 0; i < ship.size; i++) {
    const row = horiz ? r : r + i;
    const col = horiz ? c + i : c;
    grid[row][col].ship = ship;
    ship.cells.push({ r: row, c: col });
  }
}

function canPlace(grid, size, r, c, horiz) {
  for (let i = 0; i < size; i++) {
    const row = horiz ? r : r + i;
    const col = horiz ? c + i : c;
    if (row < 0 || row >= GRID || col < 0 || col >= GRID) return false;
    if (grid[row][col].ship) return false;
  }
  return true;
}

function randomPlaceAll(ships, grid) {
  ships.forEach(ship => {
    let placed = false;
    while (!placed) {
      const horiz = Math.random() < 0.5;
      const r = Math.floor(Math.random() * GRID);
      const c = Math.floor(Math.random() * GRID);
      if (canPlace(grid, ship.size, r, c, horiz)) {
        placeShipOnGrid(grid, ship, r, c, horiz);
        placed = true;
      }
    }
  });
}

/* =========================================================
   GAME STATE
   ========================================================= */

/* ---- Multiplayer state (inert until mp.active = true) ---- */
const mp = {
  active:  false,   // true while in multiplayer mode
  ws:      null,    // WebSocket to relay server
  code:    null,    // room code
  num:     null,    // player number (1 or 2)
  myTurn:  false,   // whose turn it is
  meReady: false,
  opReady: false,
  opIn:    false,   // opponent in room
  firing:  false,   // waiting for ATTACK_RESULT
};

/* Reads ?server= query param; falls back to localhost for dev */
const SERVER_URL = (() => {
  const p = new URLSearchParams(window.location.search);
  return p.get('server') || 'ws://localhost:3000';
})();

const state = {
  phase: 'setup',    // 'setup' | 'battle' | 'over'
  playerGrid: null,
  enemyGrid:  null,
  playerShips: [],
  enemyShips:  [],

  // Setup
  currentShipIdx: 0,
  isHoriz: true,

  // Battle
  isPlayerTurn: true,
  shots: 0,
  hits:  0,
  sunk:  0,
  score: 0,
  highScore: parseInt(localStorage.getItem('sbHighScore') || '0'),

  // AI hunt/target
  ai: {
    mode:      'hunt',   // 'hunt' | 'target'
    queue:     [],       // cells to try in target mode
    lastHit:   null,
    direction: null,     // null | 'h' | 'v'
    firstHit:  null,
    attacked:  new Set(),
  },
};

/* =========================================================
   UI HELPERS
   ========================================================= */

const $ = id => document.getElementById(id);

function setMsg(text, cls = '') {
  const el = $('game-message');
  el.textContent = text;
  el.className = 'game-message ' + cls;
  void el.offsetWidth; // force reflow for animation restart
  el.style.animation = 'none';
  requestAnimationFrame(() => { el.style.animation = ''; });
}

function updateScoreDisplay() {
  const el = $('score-display');
  el.textContent = state.score;
  el.classList.remove('bump');
  void el.offsetWidth;
  el.classList.add('bump');
  setTimeout(() => el.classList.remove('bump'), 300);

  $('high-score-display').textContent = state.highScore;
}

function updateBattleStats() {
  $('stat-shots').textContent = state.shots;
  $('stat-hits').textContent  = state.hits;
  $('stat-accuracy').textContent =
    state.shots > 0 ? Math.round((state.hits / state.shots) * 100) + '%' : '—';
  $('stat-sunk').textContent = state.sunk + '/5';
}

/* =========================================================
   BOARD RENDERING
   ========================================================= */

const COLS = ['A','B','C','D','E','F','G','H','I','J'];

function buildBoardDOM(boardId, isPlayer) {
  const board = $(boardId);
  board.innerHTML = '';

  // Top-left corner
  const corner = document.createElement('div');
  corner.className = 'lbl';
  board.appendChild(corner);

  // Column labels
  COLS.forEach(c => {
    const lbl = document.createElement('div');
    lbl.className = 'lbl';
    lbl.textContent = c;
    board.appendChild(lbl);
  });

  // Rows
  for (let r = 0; r < GRID; r++) {
    // Row label
    const rowLbl = document.createElement('div');
    rowLbl.className = 'lbl';
    rowLbl.textContent = r + 1;
    board.appendChild(rowLbl);

    for (let c = 0; c < GRID; c++) {
      const cell = document.createElement('div');
      cell.className = 'cell';
      cell.dataset.r = r;
      cell.dataset.c = c;

      if (isPlayer) {
        cell.addEventListener('mouseover', onPlayerCellHover);
        cell.addEventListener('mouseout',  onPlayerCellOut);
        cell.addEventListener('click',     onPlayerCellClick);
      } else {
        cell.addEventListener('click', onEnemyCellClick);
      }

      board.appendChild(cell);
    }
  }
}

function getCell(boardId, r, c) {
  return $(boardId).querySelector(`[data-r="${r}"][data-c="${c}"]`);
}

function refreshPlayerBoard() {
  for (let r = 0; r < GRID; r++) {
    for (let c = 0; c < GRID; c++) {
      const cell = getCell('player-board', r, c);
      const data = state.playerGrid[r][c];
      cell.className = 'cell';
      if (data.ship) cell.classList.add('ship');
      if (data.attacked) {
        cell.classList.add(data.ship ? 'hit' : 'miss');
        if (data.ship && data.ship.sunk) cell.classList.add('sunk');
      }
    }
  }
}

function refreshEnemyBoard() {
  for (let r = 0; r < GRID; r++) {
    for (let c = 0; c < GRID; c++) {
      const cell = getCell('enemy-board', r, c);
      const data = state.enemyGrid[r][c];
      cell.className = 'cell';
      if (data.attacked) {
        // In multiplayer we don't know ship positions upfront — use mpHit/mpSunk flags
        const isHit  = mp.active ? data.mpHit  : !!data.ship;
        const isSunk = mp.active ? data.mpSunk  : (data.ship && data.ship.sunk);
        cell.classList.add(isHit ? 'hit' : 'miss');
        if (isSunk) cell.classList.add('sunk');
      } else if (state.phase === 'battle' && state.isPlayerTurn && (!mp.active || !mp.firing)) {
        cell.classList.add('attackable');
      }
    }
  }
}

/* =========================================================
   FLEET STATUS BAR
   ========================================================= */

function buildFleetStatus(containerId, ships) {
  const el = $(containerId);
  el.innerHTML = '';
  ships.forEach(ship => {
    const wrap = document.createElement('div');
    wrap.className = 'fleet-ship';
    wrap.title = ship.name;
    wrap.dataset.shipId = ship.id;
    for (let i = 0; i < ship.size; i++) {
      const dot = document.createElement('div');
      dot.className = 'fleet-dot';
      wrap.appendChild(dot);
    }
    el.appendChild(wrap);
  });
}

function updateFleetDots(containerId, ship) {
  const wrap = $(containerId).querySelector(`[data-ship-id="${ship.id}"]`);
  if (!wrap) return;
  const dots = wrap.querySelectorAll('.fleet-dot');
  if (ship.sunk) {
    dots.forEach(d => { d.className = 'fleet-dot sunk'; });
  } else {
    dots.forEach((d, i) => {
      if (i < ship.hits) d.className = 'fleet-dot hit';
    });
  }
}

/* =========================================================
   SETUP PHASE
   ========================================================= */

function buildShipListUI() {
  const list = $('ship-list');
  list.innerHTML = '';
  SHIPS_CONFIG.forEach((cfg, i) => {
    const btn = document.createElement('button');
    btn.className = 'ship-btn' + (i === 0 ? ' active' : '');
    btn.dataset.idx = i;
    btn.innerHTML = `
      <span class="ship-icon">${cfg.icon}</span>
      <span>${cfg.name}</span>
      <span class="ship-cells">${'<span class="ship-cell-dot"></span>'.repeat(cfg.size)}</span>
    `;
    btn.addEventListener('click', () => selectShip(i));
    list.appendChild(btn);
  });
}

function selectShip(idx) {
  if (state.playerShips[idx].cells.length > 0) return; // already placed
  state.currentShipIdx = idx;
  document.querySelectorAll('.ship-btn').forEach((b, i) => {
    b.classList.toggle('active', i === idx);
  });
  clearPreview();
}

function markShipPlaced(idx) {
  const btns = document.querySelectorAll('.ship-btn');
  btns[idx].classList.remove('active');
  btns[idx].classList.add('placed');
}

function autoSelectNextShip() {
  for (let i = 0; i < state.playerShips.length; i++) {
    if (state.playerShips[i].cells.length === 0) {
      selectShip(i);
      return;
    }
  }
  // All placed
  $('start-btn').disabled = false;
  setMsg('All ships placed! Ready to battle. 🚀');
}

/* ---- Preview ---- */

function clearPreview() {
  document.querySelectorAll('#player-board .cell').forEach(c => {
    c.classList.remove('preview-ok', 'preview-bad');
  });
}

function showPreview(r, c) {
  clearPreview();
  const ship = state.playerShips[state.currentShipIdx];
  if (!ship || ship.cells.length > 0) return;

  const size   = ship.size;
  const horiz  = state.isHoriz;
  const valid  = canPlace(state.playerGrid, size, r, c, horiz);

  for (let i = 0; i < size; i++) {
    const pr = horiz ? r : r + i;
    const pc = horiz ? c + i : c;
    if (pr < 0 || pr >= GRID || pc < 0 || pc >= GRID) continue;
    const cell = getCell('player-board', pr, pc);
    cell.classList.add(valid ? 'preview-ok' : 'preview-bad');
  }
}

/* ---- Hover / Click handlers for setup ---- */

function onPlayerCellHover(e) {
  if (state.phase !== 'setup') return;
  const r = +e.currentTarget.dataset.r;
  const c = +e.currentTarget.dataset.c;
  showPreview(r, c);
}

function onPlayerCellOut() {
  if (state.phase !== 'setup') return;
  clearPreview();
}

function onPlayerCellClick(e) {
  if (state.phase !== 'setup') return;
  const r = +e.currentTarget.dataset.r;
  const c = +e.currentTarget.dataset.c;
  const ship = state.playerShips[state.currentShipIdx];
  if (!ship || ship.cells.length > 0) return;

  if (!canPlace(state.playerGrid, ship.size, r, c, state.isHoriz)) {
    setMsg('Cannot place ship there!');
    return;
  }

  placeShipOnGrid(state.playerGrid, ship, r, c, state.isHoriz);
  markShipPlaced(state.currentShipIdx);
  clearPreview();
  refreshPlayerBoard();
  $('reset-btn').disabled = false;
  updateFleetDots('player-fleet', ship);
  autoSelectNextShip();
}

/* =========================================================
   BATTLE PHASE
   ========================================================= */

function onEnemyCellClick(e) {
  if (state.phase !== 'battle') return;
  const r = +e.currentTarget.dataset.r;
  const c = +e.currentTarget.dataset.c;
  if (state.enemyGrid[r][c].attacked) return;

  if (mp.active) {
    if (!mp.myTurn || mp.firing) return;
    mpSendAttack(r, c);
  } else {
    if (!state.isPlayerTurn) return;
    playerAttack(r, c);
  }
}

function playerAttack(r, c) {
  SFX.fire();

  const cell = state.enemyGrid[r][c];
  cell.attacked = true;
  state.shots++;

  const ship = cell.ship;
  if (ship) {
    ship.hits++;
    state.hits++;
    state.score += SCORE.HIT;

    if (ship.hits === ship.size) {
      ship.sunk = true;
      state.sunk++;
      state.score += ship.size * SCORE.SUNK_MULT;
      ship.cells.forEach(({ r: sr, c: sc }) => {
        getCell('enemy-board', sr, sc).className = 'cell sunk';
      });
      updateFleetDots('enemy-fleet', ship);
      setTimeout(() => SFX.success(), 80);
      setMsg(`💥 You sunk the enemy ${ship.name}! +${ship.size * SCORE.SUNK_MULT} bonus`, 'sunk-msg');
    } else {
      getCell('enemy-board', r, c).className = 'cell hit';
      setMsg(`🔥 Hit! +${SCORE.HIT} pts`, 'hit-msg');
    }
  } else {
    getCell('enemy-board', r, c).className = 'cell miss';
    setTimeout(() => SFX.miss(), 60);
    setMsg('💧 Miss!', 'miss-msg');
  }

  updateScoreDisplay();
  updateBattleStats();

  if (checkWin()) return;

  // Disable enemy board clicks while computer thinks
  state.isPlayerTurn = false;
  setTurnIndicator(false);
  refreshEnemyBoard();

  setTimeout(computerTurn, 850);
}

function computerTurn() {
  if (state.phase !== 'battle') return;
  if (mp.active) return; // no AI in multiplayer

  SFX.fire();

  const { r, c } = aiChooseCell();
  const ai = state.ai;
  ai.attacked.add(`${r},${c}`);

  const cell = state.playerGrid[r][c];
  cell.attacked = true;

  const ship = cell.ship;
  if (ship) {
    ship.hits++;
    if (ship.hits === ship.size) {
      ship.sunk = true;
      ship.cells.forEach(({ r: sr, c: sc }) => {
        getCell('player-board', sr, sc).className = 'cell sunk';
      });
      updateFleetDots('player-fleet', ship);
      // Reset AI to hunt mode after sinking
      ai.mode = 'hunt';
      ai.queue = [];
      ai.direction = null;
      ai.lastHit = null;
      ai.firstHit = null;
    } else {
      getCell('player-board', r, c).className = 'cell ship hit';
      aiOnHit(r, c);
    }
  } else {
    getCell('player-board', r, c).className = 'cell miss';
    aiOnMiss(r, c);
  }

  if (checkLoss()) return;

  state.isPlayerTurn = true;
  setTurnIndicator(true);
  refreshEnemyBoard();
}

/* =========================================================
   AI (Hunt / Target)
   ========================================================= */

function aiChooseCell() {
  const ai = state.ai;

  if (ai.mode === 'target' && ai.queue.length > 0) {
    // Pop from queue, skip already attacked
    while (ai.queue.length > 0) {
      const next = ai.queue.shift();
      if (!ai.attacked.has(`${next.r},${next.c}`) &&
          next.r >= 0 && next.r < GRID &&
          next.c >= 0 && next.c < GRID) {
        return next;
      }
    }
    // Queue exhausted without finding unattacked cell
    ai.mode = 'hunt';
    ai.direction = null;
  }

  // Hunt mode: parity/checkerboard + random fallback
  const candidates = [];
  for (let r = 0; r < GRID; r++) {
    for (let c = 0; c < GRID; c++) {
      if (!ai.attacked.has(`${r},${c}`)) {
        if ((r + c) % 2 === 0) candidates.push({ r, c }); // checkerboard
      }
    }
  }
  if (candidates.length === 0) {
    // Fallback: any unattacked
    for (let r = 0; r < GRID; r++)
      for (let c = 0; c < GRID; c++)
        if (!ai.attacked.has(`${r},${c}`)) candidates.push({ r, c });
  }
  return candidates[Math.floor(Math.random() * candidates.length)];
}

function aiOnHit(r, c) {
  const ai = state.ai;
  if (ai.mode === 'hunt') {
    ai.mode = 'hunt'; // will transition to target next
    ai.firstHit = { r, c };
    ai.lastHit  = { r, c };
    ai.mode = 'target';
    ai.direction = null;
    ai.queue = adjacentCells(r, c, ai.attacked);
  } else {
    // Already in target — refine direction
    if (ai.direction === null && ai.firstHit) {
      ai.direction = (r === ai.firstHit.r) ? 'h' : 'v';
    }
    ai.lastHit = { r, c };
    // Add cells in confirmed direction
    if (ai.direction === 'h') {
      ai.queue = [
        { r, c: c + 1 }, { r, c: c - 1 },
        { r, c: ai.firstHit.c + 1 }, { r, c: ai.firstHit.c - 1 },
      ];
    } else if (ai.direction === 'v') {
      ai.queue = [
        { r: r + 1, c }, { r: r - 1, c },
        { r: ai.firstHit.r + 1, c }, { r: ai.firstHit.r - 1, c },
      ];
    } else {
      ai.queue = adjacentCells(r, c, ai.attacked);
    }
  }
}

function aiOnMiss(r, c) {
  const ai = state.ai;
  if (ai.mode === 'target' && ai.direction !== null && ai.queue.length === 0) {
    // Reverse direction from firstHit
    const fh = ai.firstHit;
    if (fh) {
      ai.queue = ai.direction === 'h'
        ? [{ r: fh.r, c: fh.c - 1 }, { r: fh.r, c: fh.c + 1 }]
        : [{ r: fh.r - 1, c: fh.c }, { r: fh.r + 1, c: fh.c }];
    }
  }
}

function adjacentCells(r, c, attacked) {
  return [
    { r: r - 1, c }, { r: r + 1, c },
    { r, c: c - 1 }, { r, c: c + 1 },
  ].filter(p =>
    p.r >= 0 && p.r < GRID &&
    p.c >= 0 && p.c < GRID &&
    !attacked.has(`${p.r},${p.c}`)
  );
}

/* =========================================================
   WIN / LOSS
   ========================================================= */

function checkWin() {
  if (state.enemyShips.every(s => s.sunk)) {
    state.score += SCORE.WIN_BONUS;
    if (state.score > state.highScore) {
      state.highScore = state.score;
      localStorage.setItem('sbHighScore', state.highScore);
    }
    updateScoreDisplay();
    endGame(true);
    return true;
  }
  return false;
}

function checkLoss() {
  if (state.playerShips.every(s => s.sunk)) {
    if (state.score > state.highScore) {
      state.highScore = state.score;
      localStorage.setItem('sbHighScore', state.highScore);
    }
    updateScoreDisplay();
    endGame(false);
    return true;
  }
  return false;
}

function endGame(won) {
  state.phase = 'over';
  setTimeout(() => (won ? SFX.victory() : SFX.defeat()), 350);
  $('result-icon').textContent    = won ? '🏆' : '💀';
  $('result-title').textContent   = won ? 'VICTORY!' : 'DEFEAT!';
  $('result-title').className     = 'result-title' + (won ? '' : ' defeat');
  $('res-score').textContent      = state.score;
  $('res-accuracy').textContent   =
    state.shots > 0 ? Math.round((state.hits / state.shots) * 100) + '%' : '—';
  $('res-sunk').textContent       = state.sunk + '/5';

  const isNewHigh = state.score >= state.highScore && state.score > 0;
  $('new-high').classList.toggle('hidden', !isNewHigh || !won);

  $('game-over').classList.remove('hidden');
}

/* =========================================================
   TURN INDICATOR
   ========================================================= */

function setTurnIndicator(playerTurn) {
  const el = $('turn-indicator');
  if (playerTurn) {
    el.textContent = 'YOUR TURN — FIRE!';
    el.className = 'turn-indicator';
  } else {
    el.textContent = 'ENEMY ATTACKING…';
    el.className = 'turn-indicator enemy-turn';
  }
}

/* =========================================================
   INIT / RESET
   ========================================================= */

function initGame() {
  // Tear down any active multiplayer session
  if (mp.active || mp.ws) {
    mp.ws?.close();
    mp.ws      = null;
    mp.active  = false;
    mp.code    = null;
    mp.num     = null;
    mp.myTurn  = false;
    mp.meReady = false;
    mp.opReady = false;
    mp.opIn    = false;
    mp.firing  = false;
  }

  state.phase          = 'setup';
  state.playerGrid     = makeGrid();
  state.enemyGrid      = makeGrid();
  state.playerShips    = SHIPS_CONFIG.map((cfg, i) => makeShip(cfg, i));
  state.enemyShips     = SHIPS_CONFIG.map((cfg, i) => makeShip(cfg, i));
  state.currentShipIdx = 0;
  state.isHoriz        = true;
  state.isPlayerTurn   = true;
  state.shots          = 0;
  state.hits           = 0;
  state.sunk           = 0;
  state.score          = 0;
  state.ai = { mode: 'hunt', queue: [], lastHit: null, direction: null, firstHit: null, attacked: new Set() };

  // Build boards (ready for when we reveal the setup panel)
  buildBoardDOM('player-board', true);
  buildBoardDOM('enemy-board',  false);
  buildFleetStatus('player-fleet', state.playerShips);
  buildFleetStatus('enemy-fleet',  state.enemyShips);
  buildShipListUI();

  // Show mode select, hide everything else
  $('mode-select').classList.remove('hidden');
  $('lobby').classList.add('hidden');
  $('setup-phase').classList.add('hidden');
  $('battle-phase').classList.add('hidden');
  $('game-over').classList.add('hidden');
  $('mp-ready-bar').classList.add('hidden');
  $('start-btn').textContent = 'START BATTLE';
  $('start-btn').disabled = true;
  $('reset-btn').disabled = true;

  updateScoreDisplay();
  updateBattleStats();
  setMsg('Choose a mode to begin!');
}

function startBattle() {
  state.phase = 'battle';
  $('setup-phase').classList.add('hidden');
  $('battle-phase').classList.remove('hidden');
  $('start-btn').disabled = true;

  // Remove placement listeners from player board
  document.querySelectorAll('#player-board .cell').forEach(cell => {
    cell.removeEventListener('mouseover', onPlayerCellHover);
    cell.removeEventListener('mouseout',  onPlayerCellOut);
    cell.removeEventListener('click',     onPlayerCellClick);
  });

  refreshPlayerBoard();
  refreshEnemyBoard();
  setTurnIndicator(true);
  setMsg('Game on! Click a cell in Enemy Waters to fire. 🎯');
}

function resetSetup() {
  state.playerGrid  = makeGrid();
  state.playerShips = SHIPS_CONFIG.map((cfg, i) => makeShip(cfg, i));
  state.currentShipIdx = 0;
  buildBoardDOM('player-board', true);
  buildFleetStatus('player-fleet', state.playerShips);
  buildShipListUI();
  $('start-btn').disabled = true;
  $('reset-btn').disabled = true;
  setMsg('Board reset. Place your ships!');
}

/* =========================================================
   EVENT LISTENERS
   ========================================================= */

document.addEventListener('keydown', e => {
  if (e.key === 'r' || e.key === 'R') {
    if (state.phase === 'setup') {
      state.isHoriz = !state.isHoriz;
      setMsg('Orientation: ' + (state.isHoriz ? 'Horizontal →' : 'Vertical ↓'));
    }
  }
});

$('rotate-btn').addEventListener('click', () => {
  if (state.phase !== 'setup') return;
  state.isHoriz = !state.isHoriz;
  setMsg('Orientation: ' + (state.isHoriz ? 'Horizontal →' : 'Vertical ↓'));
});

$('random-btn').addEventListener('click', () => {
  if (state.phase !== 'setup') return;
  state.playerGrid  = makeGrid();
  state.playerShips = SHIPS_CONFIG.map((cfg, i) => makeShip(cfg, i));
  randomPlaceAll(state.playerShips, state.playerGrid);

  buildBoardDOM('player-board', true);
  buildFleetStatus('player-fleet', state.playerShips);
  buildShipListUI();

  // Mark all as placed in UI
  state.playerShips.forEach((_, i) => markShipPlaced(i));
  refreshPlayerBoard();
  state.playerShips.forEach(ship => updateFleetDots('player-fleet', ship));

  $('start-btn').disabled = false;
  $('reset-btn').disabled = false;
  setMsg('Ships placed randomly! Ready to battle. 🚀');
});

$('reset-btn').addEventListener('click', resetSetup);

$('start-btn').addEventListener('click', () => {
  if (mp.active) mpSignalReady();
  else startBattle();
});

$('play-again-btn').addEventListener('click', initGame);

$('mute-btn').addEventListener('click', () => {
  const muted = SFX.toggleMute();
  $('mute-btn').textContent = muted ? '🔇' : '🔊';
  $('mute-btn').classList.toggle('muted', muted);
  $('mute-btn').title = muted ? 'Unmute' : 'Mute';
});

/* =========================================================
   MODE SELECT EVENT LISTENERS
   ========================================================= */

$('sp-btn').addEventListener('click', () => {
  mp.active = false;
  $('mode-select').classList.add('hidden');
  // Single player: pre-populate enemy ships and show setup
  randomPlaceAll(state.enemyShips, state.enemyGrid);
  buildFleetStatus('enemy-fleet', state.enemyShips);
  $('setup-phase').classList.remove('hidden');
  setMsg('Select a ship below and place it on your grid!');
});

$('mp-btn').addEventListener('click', () => {
  $('mode-select').classList.add('hidden');
  // Reset lobby to initial state
  $('lobby-pre').classList.remove('hidden');
  $('lobby-room').classList.add('hidden');
  $('lobby-error').classList.add('hidden');
  $('lobby-waiting').classList.remove('hidden');
  $('lobby-joined').classList.add('hidden');
  $('join-input').value = '';
  $('lobby').classList.remove('hidden');
  setMsg('Create a room or enter a code to join your friend!');
});

$('back-btn').addEventListener('click', () => {
  mp.ws?.close();
  mp.ws = null;
  $('lobby').classList.add('hidden');
  $('mode-select').classList.remove('hidden');
  setMsg('Choose a mode to begin!');
});

$('create-btn').addEventListener('click', () => {
  $('lobby-error').classList.add('hidden');
  mpConnect(() => mpSend({ type: 'CREATE_ROOM' }));
});

$('join-btn').addEventListener('click', () => {
  const code = $('join-input').value.toUpperCase().trim();
  if (code.length < 2) { mpLobbyError('Enter a room code.'); return; }
  $('lobby-error').classList.add('hidden');
  mpConnect(() => mpSend({ type: 'JOIN_ROOM', code }));
});

$('join-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') $('join-btn').click();
});

/* =========================================================
   MULTIPLAYER
   ========================================================= */

/* ---- WebSocket connection ---- */

function mpConnect(onOpen) {
  if (mp.ws && mp.ws.readyState < 2) mp.ws.close();
  try {
    const ws     = new WebSocket(SERVER_URL);
    mp.ws        = ws;
    ws.onopen    = () => onOpen();
    ws.onmessage = e  => mpHandle(JSON.parse(e.data));
    ws.onerror   = ()  => mpLobbyError('Cannot reach server. Is it running?');
    ws.onclose   = ()  => {
      if (mp.active && state.phase === 'battle') {
        setMsg('⚠️ Connection lost.', 'sunk-msg');
      }
    };
  } catch {
    mpLobbyError('WebSocket not supported or server unreachable.');
  }
}

function mpSend(obj) {
  if (mp.ws?.readyState === WebSocket.OPEN) mp.ws.send(JSON.stringify(obj));
}

/* ---- Incoming message router ---- */

function mpHandle(msg) {
  switch (msg.type) {

    case 'ROOM_CREATED':
      mp.code = msg.code;
      mp.num  = 1;
      $('lobby-pre').classList.add('hidden');
      $('lobby-room').classList.remove('hidden');
      $('lobby-code-display').textContent = msg.code;
      break;

    case 'ROOM_JOINED':
      // Player 2 joined a room — go straight to setup
      mp.code = msg.code;
      mp.num  = 2;
      mp.opIn = true;
      $('lobby').classList.add('hidden');
      mpInitSetup();
      setMsg(`Joined room ${msg.code}! Place your ships and click Ready.`);
      break;

    case 'OPPONENT_JOINED':
      // Player 1 learns player 2 arrived
      mp.opIn = true;
      $('lobby-waiting').classList.add('hidden');
      $('lobby-joined').classList.remove('hidden');
      setTimeout(() => {
        $('lobby').classList.add('hidden');
        mpInitSetup();
        setMsg('Opponent joined! Place your ships and click Ready.');
      }, 1000);
      break;

    case 'OPPONENT_READY':
      mp.opReady = true;
      $('mp-dot-op').classList.add('ready');
      setMsg(mp.meReady ? 'Both ready — waiting for server…' : 'Opponent is ready! Finish placing your ships.');
      break;

    case 'GAME_START':
      mp.myTurn          = msg.yourTurn;
      state.isPlayerTurn = mp.myTurn;
      mpStartBattle();
      break;

    case 'ATTACK':
      mpHandleIncomingAttack(msg);
      break;

    case 'ATTACK_RESULT':
      mpHandleAttackResult(msg);
      break;

    case 'OPPONENT_DISCONNECTED':
      setMsg('⚠️ Opponent disconnected.', 'sunk-msg');
      if (state.phase === 'battle') {
        endGame(true); // treat as win
      } else {
        $('lobby').classList.remove('hidden');
        $('setup-phase').classList.add('hidden');
        $('mp-ready-bar').classList.add('hidden');
        $('lobby-pre').classList.remove('hidden');
        $('lobby-room').classList.add('hidden');
        mpLobbyError('Opponent disconnected. Create or join a new room.');
      }
      break;

    case 'ERROR':
      mpLobbyError(msg.text || 'Server error.');
      break;
  }
}

/* ---- Lobby helpers ---- */

function mpLobbyError(text) {
  const el = $('lobby-error');
  el.textContent = text;
  el.classList.remove('hidden');
  setTimeout(() => el.classList.add('hidden'), 5000);
}

/* ---- Setup phase (multiplayer) ---- */

function mpInitSetup() {
  mp.active  = true;
  mp.meReady = false;
  mp.opReady = false;
  mp.firing  = false;

  // Fresh grids — enemy ships NOT pre-placed (we don't know them)
  state.phase          = 'setup';
  state.playerGrid     = makeGrid();
  state.enemyGrid      = makeGrid();
  state.playerShips    = SHIPS_CONFIG.map((cfg, i) => makeShip(cfg, i));
  state.enemyShips     = [];            // unused in MP
  state.currentShipIdx = 0;
  state.isHoriz        = true;
  state.shots = 0; state.hits = 0; state.sunk = 0; state.score = 0;

  buildBoardDOM('player-board', true);
  buildBoardDOM('enemy-board',  false);
  buildFleetStatus('player-fleet', state.playerShips);
  $('enemy-fleet').innerHTML = '';      // revealed as ships are sunk
  buildShipListUI();

  $('mode-select').classList.add('hidden');
  $('setup-phase').classList.remove('hidden');
  $('battle-phase').classList.add('hidden');
  $('game-over').classList.add('hidden');
  $('mp-ready-bar').classList.remove('hidden');
  $('mp-dot-me').classList.remove('ready');
  $('mp-dot-op').classList.remove('ready');

  const btn = $('start-btn');
  btn.textContent = 'READY';
  btn.disabled = true;
  $('reset-btn').disabled = true;

  updateScoreDisplay();
  updateBattleStats();
}

/* ---- Signal readiness ---- */

function mpSignalReady() {
  if (mp.meReady) return;
  mp.meReady = true;
  $('mp-dot-me').classList.add('ready');
  $('start-btn').disabled    = true;
  $('start-btn').textContent = 'WAITING…';
  mpSend({ type: 'READY' });
  setMsg(mp.opReady ? 'Both ready! Starting…' : 'Waiting for opponent to be ready…');
}

/* ---- Battle phase (multiplayer) ---- */

function mpStartBattle() {
  state.phase = 'battle';
  $('setup-phase').classList.add('hidden');
  $('battle-phase').classList.remove('hidden');
  $('mp-ready-bar').classList.add('hidden');

  document.querySelectorAll('#player-board .cell').forEach(cell => {
    cell.removeEventListener('mouseover', onPlayerCellHover);
    cell.removeEventListener('mouseout',  onPlayerCellOut);
    cell.removeEventListener('click',     onPlayerCellClick);
  });

  refreshPlayerBoard();
  refreshEnemyBoard();
  setTurnIndicator(mp.myTurn);
  setMsg(mp.myTurn
    ? 'Battle! Click a cell in Enemy Waters to fire. 🎯'
    : 'Battle! Waiting for opponent to fire first…');
}

/* ---- Player fires in multiplayer ---- */

function mpSendAttack(r, c) {
  if (mp.firing) return;
  mp.firing = true;
  refreshEnemyBoard();          // removes 'attackable' class while waiting
  mpSend({ type: 'ATTACK', r, c });
  setMsg('⏳ Fired! Awaiting result…');
}

/* ---- Opponent fires at us ---- */

function mpHandleIncomingAttack({ r, c }) {
  SFX.fire();

  const cell = state.playerGrid[r][c];
  cell.attacked = true;
  const ship = cell.ship;

  const result = { type: 'ATTACK_RESULT', r, c, hit: !!ship, sunk: false };

  if (ship) {
    ship.hits++;
    if (ship.hits === ship.size) {
      ship.sunk = true;
      result.sunk     = true;
      result.shipName = ship.name;
      result.cells    = ship.cells.map(({ r: sr, c: sc }) => ({ r: sr, c: sc }));
      ship.cells.forEach(({ r: sr, c: sc }) => {
        getCell('player-board', sr, sc).className = 'cell sunk';
      });
      updateFleetDots('player-fleet', ship);
    } else {
      getCell('player-board', r, c).className = 'cell ship hit';
      updateFleetDots('player-fleet', ship);
    }
  } else {
    getCell('player-board', r, c).className = 'cell miss';
  }

  if (state.playerShips.every(s => s.sunk)) result.gameOver = true;

  mpSend(result);

  if (result.gameOver) { endGame(false); return; }

  // Now it is our turn
  mp.myTurn          = true;
  state.isPlayerTurn = true;
  setTurnIndicator(true);
  refreshEnemyBoard();
}

/* ---- Result of our own attack comes back ---- */

function mpHandleAttackResult(msg) {
  const { r, c, hit, sunk, shipName, cells, gameOver } = msg;
  mp.firing = false;
  state.shots++;

  const data = state.enemyGrid[r][c];
  data.attacked = true;

  if (hit) {
    state.hits++;
    state.score += SCORE.HIT;
    data.mpHit = true;

    if (sunk) {
      data.mpSunk = true;
      state.sunk++;
      state.score += cells.length * SCORE.SUNK_MULT;
      cells.forEach(({ r: sr, c: sc }) => {
        const cd = state.enemyGrid[sr][sc];
        cd.attacked = true; cd.mpHit = true; cd.mpSunk = true;
        getCell('enemy-board', sr, sc).className = 'cell sunk';
      });
      mpRevealEnemyShip(shipName, cells.length);
      setTimeout(() => SFX.success(), 80);
      setMsg(`💥 You sunk the enemy ${shipName}! +${cells.length * SCORE.SUNK_MULT} bonus`, 'sunk-msg');
    } else {
      getCell('enemy-board', r, c).className = 'cell hit';
      setMsg(`🔥 Hit! +${SCORE.HIT} pts`, 'hit-msg');
    }
  } else {
    getCell('enemy-board', r, c).className = 'cell miss';
    setTimeout(() => SFX.miss(), 60);
    setMsg('💧 Miss!', 'miss-msg');
  }

  updateScoreDisplay();
  updateBattleStats();

  if (gameOver) {
    state.score += SCORE.WIN_BONUS;
    if (state.score > state.highScore) {
      state.highScore = state.score;
      localStorage.setItem('sbHighScore', state.highScore);
    }
    updateScoreDisplay();
    endGame(true);
    return;
  }

  // Opponent's turn
  mp.myTurn          = false;
  state.isPlayerTurn = false;
  setTurnIndicator(false);
  refreshEnemyBoard();
}

/* Add a revealed ship entry to the enemy fleet bar when sunk */
function mpRevealEnemyShip(name, size) {
  const wrap = document.createElement('div');
  wrap.className = 'fleet-ship';
  wrap.title     = name + ' (sunk)';
  for (let i = 0; i < size; i++) {
    const dot = document.createElement('div');
    dot.className = 'fleet-dot sunk';
    wrap.appendChild(dot);
  }
  $('enemy-fleet').appendChild(wrap);
}

/* =========================================================
   BOOT
   ========================================================= */

// Sync mute button to persisted preference
(function syncMuteBtn() {
  if (SFX.isMuted()) {
    $('mute-btn').textContent = '🔇';
    $('mute-btn').classList.add('muted');
    $('mute-btn').title = 'Unmute';
  }
})();

initGame();
