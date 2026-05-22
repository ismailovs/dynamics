'use strict';
/* =====================================================================
   Ship Battle — WebSocket relay server
   Responsibilities:
     · Create / manage rooms (4-char codes, max 2 players each)
     · Relay ATTACK and ATTACK_RESULT between the two players
     · Coordinate READY → GAME_START (decides who fires first)
     · Notify on disconnect
   No game logic lives here — clients validate everything themselves.
   ===================================================================== */

const { WebSocketServer } = require('ws');
const PORT = process.env.PORT || 3000;

// rooms: Map<code, { p1: WebSocket|null, p2: WebSocket|null, ready: Set<1|2> }>
const rooms = new Map();

// Omit visually ambiguous characters (0/O, 1/I)
const CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';

function genCode() {
  let code;
  do {
    code = Array.from({ length: 4 }, () =>
      CHARS[Math.floor(Math.random() * CHARS.length)]
    ).join('');
  } while (rooms.has(code));
  return code;
}

function send(ws, obj) {
  if (ws && ws.readyState === 1 /* OPEN */) ws.send(JSON.stringify(obj));
}

function relay(ws, obj) {
  const room = rooms.get(ws.roomCode);
  if (!room) return;
  const op = room.p1 === ws ? room.p2 : room.p1;
  send(op, obj);
}

/* ---- Server ---- */

const wss = new WebSocketServer({ port: PORT });

wss.on('connection', ws => {
  ws.roomCode  = null;
  ws.playerNum = null;
  ws.isAlive   = true;

  ws.on('pong', () => { ws.isAlive = true; });

  ws.on('message', raw => {
    let msg;
    try { msg = JSON.parse(raw); } catch { return; }

    switch (msg.type) {

      case 'CREATE_ROOM': {
        const code = genCode();
        rooms.set(code, { p1: ws, p2: null, ready: new Set() });
        ws.roomCode  = code;
        ws.playerNum = 1;
        send(ws, { type: 'ROOM_CREATED', code, playerNum: 1 });
        break;
      }

      case 'JOIN_ROOM': {
        const code = String(msg.code || '').toUpperCase().trim();
        const room  = rooms.get(code);
        if (!room)   { send(ws, { type: 'ERROR', text: 'Room not found.' });  return; }
        if (room.p2) { send(ws, { type: 'ERROR', text: 'Room is full.' });    return; }
        room.p2 = ws;
        ws.roomCode  = code;
        ws.playerNum = 2;
        send(ws,      { type: 'ROOM_JOINED',    code, playerNum: 2 });
        send(room.p1, { type: 'OPPONENT_JOINED' });
        break;
      }

      case 'READY': {
        const room = rooms.get(ws.roomCode);
        if (!room) return;
        room.ready.add(ws.playerNum);
        relay(ws, { type: 'OPPONENT_READY' });
        if (room.ready.size === 2) {
          const first = Math.random() < 0.5 ? 1 : 2;
          send(room.p1, { type: 'GAME_START', yourTurn: first === 1 });
          send(room.p2, { type: 'GAME_START', yourTurn: first === 2 });
          room.ready.clear();
        }
        break;
      }

      // Pure relay — the receiving client validates and responds
      case 'ATTACK':
      case 'ATTACK_RESULT':
        relay(ws, msg);
        break;

      default:
        break;
    }
  });

  ws.on('close', () => {
    if (!ws.roomCode) return;
    relay(ws, { type: 'OPPONENT_DISCONNECTED' });
    rooms.delete(ws.roomCode);
    console.log(`[-] Room ${ws.roomCode} closed (player ${ws.playerNum} left). Rooms open: ${rooms.size}`);
  });

  ws.on('error', err => console.error('[WS error]', err.message));
  console.log(`[+] Client connected. Rooms open: ${rooms.size}`);
});

// Heartbeat — kill zombie connections every 30 s
const heartbeat = setInterval(() => {
  wss.clients.forEach(ws => {
    if (!ws.isAlive) return ws.terminate();
    ws.isAlive = false;
    ws.ping();
  });
}, 30_000);

wss.on('close', () => clearInterval(heartbeat));

console.log(`⚓  Ship Battle server  ·  ws://localhost:${PORT}`);
console.log(`   Set SERVER env var to override port.`);
console.log(`   Clients connect via ?server=ws://<host>:${PORT}`);
