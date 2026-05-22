/* =============================================================
   SHIP BATTLE — Sound Effects
   All sounds synthesised with the Web Audio API; no audio files needed.
   ============================================================= */

const SFX = (() => {
  let _ctx    = null;
  let _master = null;
  let _muted  = JSON.parse(localStorage.getItem('sbMuted') || 'false');

  /* ---- Context ---- */

  function ac() {
    if (!_ctx) {
      const Ctor = window.AudioContext || window.webkitAudioContext;
      if (!Ctor) return null;
      _ctx    = new Ctor();
      _master = _ctx.createGain();
      _master.gain.value = _muted ? 0 : 1;
      _master.connect(_ctx.destination);
    }
    if (_ctx.state === 'suspended') _ctx.resume();
    return _ctx;
  }

  function dest() { ac(); return _master; }

  /* ---- Primitive builders ---- */

  function mkNoise(seconds) {
    const c   = ac(); if (!c) return null;
    const len = Math.ceil(c.sampleRate * seconds);
    const buf = c.createBuffer(1, len, c.sampleRate);
    const d   = buf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
    const src = c.createBufferSource();
    src.buffer = buf;
    return src;
  }

  function mkOsc(type, freq) {
    const c = ac(); if (!c) return null;
    const o = c.createOscillator();
    o.type = type;
    o.frequency.value = freq;
    return o;
  }

  function mkFilter(type, freq, Q = 1) {
    const c = ac(); if (!c) return null;
    const f = c.createBiquadFilter();
    f.type = type;
    f.frequency.value = freq;
    f.Q.value = Q;
    return f;
  }

  function mkGain() {
    const c = ac(); if (!c) return null;
    return c.createGain();
  }

  // Chain nodes left→right, last node goes to master output
  function chain(...nodes) {
    for (let i = 0; i < nodes.length - 1; i++) nodes[i].connect(nodes[i + 1]);
    nodes[nodes.length - 1].connect(dest());
  }

  /* ---- Reusable envelope ---- */

  function env(gainNode, t, startVal, endVal, duration) {
    const g = gainNode.gain;
    g.cancelScheduledValues(t);
    g.setValueAtTime(startVal, t);
    g.exponentialRampToValueAtTime(Math.max(endVal, 0.00001), t + duration);
  }

  /* ---- Explosion core (shared by fire & success) ---- */

  function explosion(t, scale = 1) {
    const c   = ac(); if (!c) return;
    const dur = 0.12 + scale * 0.32;

    // White-noise body through falling lowpass
    const n  = mkNoise(dur + 0.05);
    const lp = mkFilter('lowpass', 1);
    const ng = mkGain();
    lp.frequency.setValueAtTime(900 * scale, t);
    lp.frequency.exponentialRampToValueAtTime(55, t + dur);
    env(ng, t, scale * 0.95, 0.00001, dur);
    chain(n, lp, ng);
    n.start(t); n.stop(t + dur + 0.06);

    // Sub-bass thump
    const o  = mkOsc('sine', 120 * scale);
    const og = mkGain();
    o.frequency.setValueAtTime(90 + 60 * scale, t);
    o.frequency.exponentialRampToValueAtTime(22, t + dur * 0.7);
    env(og, t, scale * 0.85, 0.00001, dur * 0.75);
    chain(o, og);
    o.start(t); o.stop(t + dur);
  }

  /* ================================================================
     PUBLIC SOUNDS
     ================================================================ */

  return {

    toggleMute() {
      _muted = !_muted;
      localStorage.setItem('sbMuted', _muted);
      if (_master) {
        const c = ac();
        _master.gain.setTargetAtTime(_muted ? 0 : 1, c.currentTime, 0.03);
      }
      return _muted;
    },

    isMuted() { return _muted; },

    /* ---- FIRE: cannon shot ---- */
    fire() {
      const c = ac(); if (!c) return;
      const t = c.currentTime;

      // Sharp crack (short hi-freq noise burst)
      const crack  = mkNoise(0.06);
      const crackF = mkFilter('highpass', 2000);
      const crackG = mkGain();
      env(crackG, t, 0.55, 0.00001, 0.05);
      chain(crack, crackF, crackG);
      crack.start(t); crack.stop(t + 0.07);

      // Main boom
      explosion(t + 0.01, 0.65);
    },

    /* ---- MISS: water splash ---- */
    miss() {
      const c = ac(); if (!c) return;
      const t = c.currentTime;

      // Bandpass noise: high freqs first, then splashy low rumble
      const n  = mkNoise(0.55);
      const bp = mkFilter('bandpass', 3200, 2.5);
      const g  = mkGain();
      bp.frequency.setValueAtTime(3200, t);
      bp.frequency.exponentialRampToValueAtTime(500, t + 0.45);
      env(g, t, 0.38, 0.00001, 0.48);
      chain(n, bp, g);
      n.start(t); n.stop(t + 0.56);

      // Soft ripple tone
      const o  = mkOsc('sine', 320);
      const og = mkGain();
      o.frequency.setValueAtTime(320, t + 0.05);
      o.frequency.exponentialRampToValueAtTime(180, t + 0.35);
      env(og, t + 0.05, 0.12, 0.00001, 0.3);
      chain(o, og);
      o.start(t + 0.05); o.stop(t + 0.4);
    },

    /* ---- SUCCESS: ship sunk ---- */
    success() {
      const c = ac(); if (!c) return;
      const t = c.currentTime;

      // Big explosion
      explosion(t, 1.4);

      // Ascending victory chime: C5 E5 G5 C6
      [523.25, 659.25, 783.99, 1046.5].forEach((freq, i) => {
        const o  = mkOsc('sine', freq);
        const g  = mkGain();
        const st = t + 0.38 + i * 0.13;
        env(g, st, 0.5, 0.00001, 0.38);
        chain(o, g);
        o.start(st); o.stop(st + 0.42);
      });
    },

    /* ---- VICTORY: game won ---- */
    victory() {
      const c = ac(); if (!c) return;
      const t = c.currentTime;

      // Fanfare melody
      [
        [523.25, 0.00, 0.18],   // C5
        [659.25, 0.16, 0.18],   // E5
        [783.99, 0.32, 0.18],   // G5
        [1046.5, 0.48, 0.45],   // C6
        [880.00, 0.96, 0.18],   // A5
        [1046.5, 1.14, 0.70],   // C6 (hold)
      ].forEach(([freq, dt, dur]) => {
        const o  = mkOsc('sine', freq);
        const g  = mkGain();
        const st = t + dt;
        g.gain.setValueAtTime(0.0001, st);
        g.gain.linearRampToValueAtTime(0.55, st + 0.02);
        g.gain.setValueAtTime(0.55, st + dur * 0.72);
        g.gain.exponentialRampToValueAtTime(0.00001, st + dur);
        chain(o, g);
        o.start(st); o.stop(st + dur + 0.02);
      });

      // Bass harmony
      [
        [130.81, 0.00, 0.55],
        [164.81, 0.32, 0.55],
        [196.00, 0.64, 0.55],
        [261.63, 0.96, 0.90],
      ].forEach(([freq, dt, dur]) => {
        const o  = mkOsc('triangle', freq);
        const g  = mkGain();
        const st = t + dt;
        env(g, st, 0.22, 0.00001, dur);
        chain(o, g);
        o.start(st); o.stop(st + dur + 0.02);
      });

      // Percussive intro roll (noise burst)
      const roll  = mkNoise(0.28);
      const rollF = mkFilter('bandpass', 180, 3);
      const rollG = mkGain();
      env(rollG, t, 0.45, 0.00001, 0.25);
      chain(roll, rollF, rollG);
      roll.start(t); roll.stop(t + 0.3);
    },

    /* ---- DEFEAT: game lost ---- */
    defeat() {
      const c = ac(); if (!c) return;
      const t = c.currentTime;

      // Descending minor phrase: G4 F4 Eb4 C4 A3
      [
        [392.00, 0.00, 0.42],
        [349.23, 0.40, 0.42],
        [311.13, 0.80, 0.42],
        [261.63, 1.20, 0.48],
        [220.00, 1.72, 0.90],
      ].forEach(([freq, dt, dur]) => {
        const o  = mkOsc('sawtooth', freq);
        const lp = mkFilter('lowpass', 700, 0.8);
        const g  = mkGain();
        const st = t + dt;
        g.gain.setValueAtTime(0.0001, st);
        g.gain.linearRampToValueAtTime(0.28, st + 0.03);
        g.gain.setValueAtTime(0.28, st + dur * 0.6);
        g.gain.exponentialRampToValueAtTime(0.00001, st + dur);
        o.connect(lp); lp.connect(g); g.connect(dest());
        o.start(st); o.stop(st + dur + 0.02);
      });

      // Low drone swell at the end
      const drone  = mkOsc('sine', 55);
      const droneG = mkGain();
      droneG.gain.setValueAtTime(0.00001, t + 1.6);
      droneG.gain.linearRampToValueAtTime(0.35, t + 2.0);
      droneG.gain.exponentialRampToValueAtTime(0.00001, t + 2.8);
      chain(drone, droneG);
      drone.start(t + 1.6); drone.stop(t + 2.9);
    },

  };
})();
