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
        cell.classList.add(data.ship ? 'hit' : 'miss');
        if (data.ship && data.ship.sunk) cell.classList.add('sunk');
      } else if (state.phase === 'battle' && state.isPlayerTurn) {
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
  if (state.phase !== 'battle' || !state.isPlayerTurn) return;
  const r = +e.currentTarget.dataset.r;
  const c = +e.currentTarget.dataset.c;
  if (state.enemyGrid[r][c].attacked) return;

  playerAttack(r, c);
}

function playerAttack(r, c) {
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
      setMsg(`💥 You sunk the enemy ${ship.name}! +${ship.size * SCORE.SUNK_MULT} bonus`, 'sunk-msg');
    } else {
      getCell('enemy-board', r, c).className = 'cell hit';
      setMsg(`🔥 Hit! +${SCORE.HIT} pts`, 'hit-msg');
    }
  } else {
    getCell('enemy-board', r, c).className = 'cell miss';
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

  // Place enemy ships randomly
  randomPlaceAll(state.enemyShips, state.enemyGrid);

  // Build boards
  buildBoardDOM('player-board', true);
  buildBoardDOM('enemy-board',  false);

  // Build fleet status
  buildFleetStatus('player-fleet', state.playerShips);
  buildFleetStatus('enemy-fleet',  state.enemyShips);

  // Build ship selector
  buildShipListUI();

  // Show/hide panels
  $('setup-phase').classList.remove('hidden');
  $('battle-phase').classList.add('hidden');
  $('game-over').classList.add('hidden');
  $('start-btn').disabled = true;
  $('reset-btn').disabled = true;

  updateScoreDisplay();
  updateBattleStats();
  setMsg('Select a ship below and place it on your grid!');
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

$('start-btn').addEventListener('click', startBattle);

$('play-again-btn').addEventListener('click', initGame);

/* =========================================================
   BOOT
   ========================================================= */

initGame();
