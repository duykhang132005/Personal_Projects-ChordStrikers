/* Metronome and tuner for one sheet. BPM is stored on this device. */
(function () {
  const root = document.getElementById('sheet-root');
  const bpmInput = document.getElementById('bpm-input');
  const tapBtn = document.getElementById('btn-tap-tempo');
  const metroBtn = document.getElementById('btn-metro');
  const tunerBtn = document.getElementById('btn-tuner');
  const readout = document.getElementById('tuner-readout');
  if (!root || !bpmInput) return;

  const songId = root.getAttribute('data-song-id');
  const prefKey = 'cs-song-' + songId;
  const NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
  const STRINGS = [
    { name: 'E2', freq: 82.41 },
    { name: 'A2', freq: 110.00 },
    { name: 'D3', freq: 146.83 },
    { name: 'G3', freq: 196.00 },
    { name: 'B3', freq: 246.94 },
    { name: 'E4', freq: 329.63 }
  ];

  function readPrefs() {
    try { return JSON.parse(localStorage.getItem(prefKey)) || {}; } catch (e) { return {}; }
  }
  function writeBpm(bpm) {
    try {
      const all = readPrefs();
      all.bpm = bpm;
      localStorage.setItem(prefKey, JSON.stringify(all));
    } catch (e) { /* private mode */ }
  }

  const saved = readPrefs();
  if (saved.bpm >= 40 && saved.bpm <= 240) bpmInput.value = String(saved.bpm);

  function currentBpm() {
    const bpm = parseInt(bpmInput.value, 10);
    if (!bpm || bpm < 40) return 40;
    if (bpm > 240) return 240;
    return bpm;
  }
  bpmInput.addEventListener('change', function () {
    bpmInput.value = String(currentBpm());
    writeBpm(currentBpm());
  });

  const taps = [];
  tapBtn.addEventListener('click', function () {
    const now = performance.now();
    if (taps.length && now - taps[taps.length - 1] > 2000) taps.length = 0;
    taps.push(now);
    if (taps.length > 5) taps.shift();
    if (taps.length < 2) return;
    let total = 0;
    for (let i = 1; i < taps.length; i++) total += taps[i] - taps[i - 1];
    const bpm = Math.round(60000 / (total / (taps.length - 1)));
    bpmInput.value = String(Math.max(40, Math.min(240, bpm)));
    writeBpm(currentBpm());
  });

  let audio = null;
  let metroTimer = null;
  let nextClick = 0;

  function clickAt(time) {
    const osc = audio.createOscillator();
    const gain = audio.createGain();
    osc.frequency.value = 1000;
    gain.gain.setValueAtTime(0.25, time);
    gain.gain.exponentialRampToValueAtTime(0.001, time + 0.04);
    osc.connect(gain);
    gain.connect(audio.destination);
    osc.start(time);
    osc.stop(time + 0.05);
  }

  function stopMetro() {
    if (metroTimer) clearInterval(metroTimer);
    metroTimer = null;
    metroBtn.textContent = 'Start metronome';
    metroBtn.setAttribute('aria-pressed', 'false');
  }

  metroBtn.addEventListener('click', function () {
    if (metroTimer) { stopMetro(); return; }
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) {
      metroBtn.textContent = 'No audio in this browser';
      return;
    }
    audio = audio || new AudioCtx();
    if (audio.state === 'suspended') audio.resume();
    const spacing = 60 / currentBpm();
    nextClick = audio.currentTime + 0.05;
    metroBtn.textContent = 'Stop metronome';
    metroBtn.setAttribute('aria-pressed', 'true');
    metroTimer = setInterval(function () {
      const horizon = audio.currentTime + 0.15;
      while (nextClick < horizon) {
        clickAt(nextClick);
        nextClick += 60 / currentBpm();
      }
    }, 40);
  });

  let tunerOn = false;
  let stream = null;
  let analyser = null;
  let tunerTimer = null;
  const buffer = new Float32Array(2048);

  function pitchFrom(samples, sampleRate) {
    let energy = 0;
    for (let i = 0; i < samples.length; i++) energy += samples[i] * samples[i];
    if (Math.sqrt(energy / samples.length) < 0.015) return null;
    const minLag = Math.floor(sampleRate / 700);
    const maxLag = Math.floor(sampleRate / 60);
    let best = 0;
    let bestLag = -1;
    for (let lag = minLag; lag <= maxLag; lag++) {
      let sum = 0;
      for (let i = 0; i < samples.length - lag; i += 2) sum += samples[i] * samples[i + lag];
      if (sum > best) { best = sum; bestLag = lag; }
    }
    if (bestLag < 1) return null;
    return sampleRate / bestLag;
  }

  function describe(freq) {
    const midi = 12 * Math.log(freq / 440) / Math.LN2 + 69;
    const rounded = Math.round(midi);
    const cents = Math.round((midi - rounded) * 100);
    const name = NAMES[((rounded % 12) + 12) % 12] + (Math.floor(rounded / 12) - 1);
    let closest = STRINGS[0];
    let gap = Infinity;
    STRINGS.forEach(function (string) {
      const d = Math.abs(1200 * Math.log(freq / string.freq) / Math.LN2);
      if (d < gap) { gap = d; closest = string; }
    });
    const stringCents = Math.round(1200 * Math.log(freq / closest.freq) / Math.LN2);
    const signed = (stringCents > 0 ? '+' : '') + stringCents;
    return name + ' (' + (cents > 0 ? '+' : '') + cents + ' cents). Closest string ' + closest.name + ' ' + signed + ' cents.';
  }

  function stopTuner() {
    tunerOn = false;
    if (tunerTimer) cancelAnimationFrame(tunerTimer);
    tunerTimer = null;
    if (stream) stream.getTracks().forEach(function (track) { track.stop(); });
    stream = null;
    tunerBtn.textContent = 'Tuner';
    tunerBtn.setAttribute('aria-pressed', 'false');
  }

  function listen() {
    if (!tunerOn || !analyser) return;
    analyser.getFloatTimeDomainData(buffer);
    const freq = pitchFrom(buffer, audio.sampleRate);
    if (freq) readout.textContent = describe(freq);
    tunerTimer = requestAnimationFrame(listen);
  }

  tunerBtn.addEventListener('click', function () {
    if (tunerOn) { stopTuner(); readout.textContent = 'Mic off'; return; }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      readout.textContent = 'This browser has no microphone. On iPhone, open the page in Safari.';
      return;
    }
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) { readout.textContent = 'This browser has no audio.'; return; }
    navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false } })
      .then(function (got) {
        stream = got;
        audio = audio || new AudioCtx();
        if (audio.state === 'suspended') audio.resume();
        const source = audio.createMediaStreamSource(stream);
        analyser = audio.createAnalyser();
        analyser.fftSize = 2048;
        source.connect(analyser);
        tunerOn = true;
        tunerBtn.textContent = 'Stop tuner';
        tunerBtn.setAttribute('aria-pressed', 'true');
        readout.textContent = 'Listening... play one string.';
        listen();
      })
      .catch(function (err) {
        if (err && (err.name === 'NotAllowedError' || err.name === 'SecurityError')) {
          readout.textContent = 'Microphone blocked. Allow it in the browser, or on iPhone open this page in Safari (the installed app often cannot use the mic).';
        } else {
          readout.textContent = 'Microphone is not available right now.';
        }
      });
  });

  window.addEventListener('pagehide', function () { stopMetro(); stopTuner(); });
})();
