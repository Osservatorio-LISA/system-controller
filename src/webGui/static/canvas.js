// ═══════════════════════════════════════════════════════════════════════════════
//  canvas.js  —  rendering canvas e interazione UI
//  Responsabilità: disegno cupola/telescopio, slider, drag, bottoni
//  Lo stato reale arriva da api.js via callback onStateUpdate + startPolling
// ═══════════════════════════════════════════════════════════════════════════════

import { logToTerminal, initTerminal } from '/webGuiStatic/terminal.js';
import { state, onStateUpdate, startPolling, POLLING_PERIOD_MS, sendAndReceive,  gotoPosition, moveModule } from '/webGuiStatic/api.js';

// ─── Stato locale UI (può divergere temporaneamente da state{} durante il drag)
let domeDeg          = 0;
let telescopeDeg     = 0;
let telescopeTiltDeg = 0;
let isSlitOpen       = false;

// ─── Canvas ──────────────────────────────────────────────────────────────────
const canvas = document.getElementById('observatoryCanvas');
const ctx    = canvas.getContext('2d');
const cx     = canvas.width  / 2;
const cy     = canvas.height / 2;

// ─── Riferimenti UI ──────────────────────────────────────────────────────────
const slideDome  = document.getElementById('slideDome');
const slideScope = document.getElementById('slideScope');
const slideTilt  = document.getElementById('slideTilt');
const lblDome    = document.getElementById('lblDome');
const lblScope   = document.getElementById('lblScope');
const lblTilt    = document.getElementById('lblTilt');
const btnSlit    = document.getElementById('btnSlit');

// ─── Costanti canvas ─────────────────────────────────────────────────────────
const outerRadius = 180;
const domeRadius  = 150;
const scopeRadius = 60;

// ─── Stato animazione ────────────────────────────────────────────────────────
let slitAnimationProgress = 0;
let isDraggingDome        = false;
let isDraggingTelescope   = false;


// ─── Init ────────────────────────────────────────────────────────────────────
function init() {
    // Ricezione stato reale da api.js
    onStateUpdate((newState) => {
        domeDeg          = newState.domeDeg;
        telescopeDeg     = newState.telescopeDeg;
        telescopeTiltDeg = newState.telescopeTiltDeg;
        isSlitOpen       = newState.isSlitOpen;
        updateUI(true);
    });
    initTerminal();
    startPolling(POLLING_PERIOD_MS);
 
    // Slider: aggiornano solo la vista locale
    slideDome.addEventListener('input',  (e) => { domeDeg          = parseFloat(e.target.value); updateUI(false); });
    slideScope.addEventListener('input', (e) => { telescopeDeg     = parseFloat(e.target.value); updateUI(false); });
    slideTilt.addEventListener('input',  (e) => { telescopeTiltDeg = parseFloat(e.target.value); updateUI(false); });
 
    // Drag canvas
    canvas.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mousemove',  handleMouseMove);
    window.addEventListener('mouseup',   () => { isDraggingDome = false; isDraggingTelescope = false; });
    canvas.addEventListener('touchstart', (e) => { e.preventDefault(); handleMouseDown(e.touches[0]); }, { passive: false });
    window.addEventListener('touchmove',  (e) => { handleMouseMove(e.touches[0]); });
    window.addEventListener('touchend',  () => { isDraggingDome = false; isDraggingTelescope = false; });
 
    updateUI(true);
    requestAnimationFrame(animationLoop);
}
// ─── Animation loop ──────────────────────────────────────────────────────────
function animationLoop() {
    let changed = false;
    if (isSlitOpen  && slitAnimationProgress < 1) { slitAnimationProgress = Math.min(1, slitAnimationProgress + 0.08); changed = true; }
    if (!isSlitOpen && slitAnimationProgress > 0) { slitAnimationProgress = Math.max(0, slitAnimationProgress - 0.08); changed = true; }
    if (changed || isDraggingDome || isDraggingTelescope) draw();
    requestAnimationFrame(animationLoop);
}

// ─── Bottone Feritoia → MOVE slit:open / slit:close ─────────────────────────
window.toggleSlit = async function () {
    const cmd = isSlitOpen ? 'MOVE slit:close' : 'MOVE slit:open';
    await sendAndReceive(cmd);
    // Lo stato reale arriverà al prossimo polling; aggiorniamo ottimisticamente
    isSlitOpen = !isSlitOpen;
    btnSlit.innerText = isSlitOpen ? 'Chiudi Feritoia' : 'Apri Feritoia';
    btnSlit.classList.toggle('active', isSlitOpen);
};

// ─── Bottone "Invia a LISA" → GOTO con angoli attuali ───────────────────────
window.sendToLisa = async function () {
    const h = Math.round(domeDeg);
    const v = Math.round(telescopeTiltDeg);
    await sendAndReceive(`GOTO ${h} ${v}`);
};

// ─── Mouse / Touch helpers ───────────────────────────────────────────────────
function getMousePos(coord) {
    const rect = canvas.getBoundingClientRect();
    return {
        x: (coord.clientX - rect.left) * (canvas.width  / rect.width),
        y: (coord.clientY - rect.top)  * (canvas.height / rect.height)
    };
}

function getAngleAndDist(x, y) {
    const dx   = x - cx, dy = y - cy;
    const dist = Math.sqrt(dx * dx + dy * dy);
    let   deg  = (Math.atan2(dx, -dy) * 180) / Math.PI;
    if (deg < 0) deg += 360;
    return { deg, dist };
}

function handleMouseDown(e) {
    const { deg, dist } = getAngleAndDist(...Object.values(getMousePos(e)));
    if      (dist <= scopeRadius)                       { isDraggingTelescope = true; telescopeDeg = deg; }
    else if (dist <= outerRadius + 10)                  { isDraggingDome      = true; domeDeg      = deg; }
    updateUI(true);
}

function handleMouseMove(e) {
    if (!isDraggingDome && !isDraggingTelescope) return;
    const { deg } = getAngleAndDist(...Object.values(getMousePos(e)));
    if (isDraggingDome)      domeDeg      = deg;
    if (isDraggingTelescope) telescopeDeg = deg;
    updateUI(true);
}

// ─── UI update ───────────────────────────────────────────────────────────────
function updateUI(updateSliders = true) {
    lblDome.innerText  = domeDeg.toFixed(1)          + '°';
    lblScope.innerText = telescopeDeg.toFixed(1)     + '°';
    lblTilt.innerText  = telescopeTiltDeg.toFixed(1) + '°';
    if (updateSliders) {
        slideDome.value  = domeDeg.toFixed(1);
        slideScope.value = telescopeDeg.toFixed(1);
        slideTilt.value  = telescopeTiltDeg.toFixed(1);
    }
    draw();
}

// ─── Draw ─────────────────────────────────────────────────────────────────────
function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Griglia cardinale
    ctx.beginPath();
    ctx.arc(cx, cy, outerRadius, 0, 2 * Math.PI);
    ctx.strokeStyle = '#f1f3f9'; ctx.lineWidth = 1; ctx.stroke();

    ctx.font = '12px sans-serif';
    ctx.fillStyle = varColor('--text-muted', '#8c96a0');
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText('N',   cx,               cy - outerRadius - 20);
    ctx.fillText('0',   cx,               cy - outerRadius - 5);
    ctx.fillText('E',   cx + outerRadius + 30, cy);
    ctx.fillText('90',  cx + outerRadius + 10, cy);
    ctx.fillText('S',   cx,               cy + outerRadius + 20);
    ctx.fillText('180', cx,               cy + outerRadius + 5);
    ctx.fillText('W',   cx - outerRadius - 30, cy);
    ctx.fillText('270', cx - outerRadius - 10, cy);

    // ── CUPOLA ────────────────────────────────────────────────────────────────
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate((domeDeg * Math.PI) / 180);

    const slitHalfWidth = 20;
    const alpha = Math.asin(slitHalfWidth / domeRadius);

    // Pannello sinistro
    ctx.save();
    ctx.beginPath();
    ctx.arc(0, 0, domeRadius, -Math.PI + alpha,  -Math.PI / 2 - alpha);
    ctx.arc(0, 0, domeRadius,  Math.PI / 2 + alpha, Math.PI - alpha);
    ctx.closePath();
    const gL = ctx.createLinearGradient(-domeRadius, 0, -slitHalfWidth, 0);
    gL.addColorStop(0, '#7a8a9e'); gL.addColorStop(1, '#b0bfc0');
    ctx.fillStyle = gL; ctx.fill();
    ctx.restore();

    // Pannello destro
    ctx.save();
    ctx.beginPath();
    ctx.arc(0, 0, domeRadius, -Math.PI / 2 + alpha, -alpha);
    ctx.arc(0, 0, domeRadius,  alpha,                Math.PI / 2 - alpha);
    ctx.closePath();
    const gR = ctx.createLinearGradient(slitHalfWidth, 0, domeRadius, 0);
    gR.addColorStop(0, '#b0bfc0'); gR.addColorStop(1, '#7a8a9e');
    ctx.fillStyle = gR; ctx.fill();
    ctx.restore();

    // Striscia centrale
    ctx.beginPath();
    ctx.rect(-slitHalfWidth, -domeRadius * Math.cos(alpha), slitHalfWidth * 2, domeRadius * Math.cos(alpha) * 2);
    ctx.fillStyle = 'rgba(220,225,230,0.6)'; ctx.fill();
    ctx.beginPath();
    ctx.moveTo(-slitHalfWidth, -domeRadius * Math.cos(alpha));
    ctx.lineTo(-slitHalfWidth,  domeRadius * Math.cos(alpha));
    ctx.moveTo( slitHalfWidth, -domeRadius * Math.cos(alpha));
    ctx.lineTo( slitHalfWidth,  domeRadius * Math.cos(alpha));
    ctx.strokeStyle = '#000066'; ctx.lineWidth = 1; ctx.stroke();

    ctx.beginPath();
    ctx.arc(0, 0, domeRadius, 0, 2 * Math.PI);
    ctx.strokeStyle = '#000066'; ctx.lineWidth = 1.5; ctx.stroke();

    // Animazione feritoia
    const base = 0.22, maxO = 0.15, curO = maxO * slitAnimationProgress;
    ctx.lineWidth = 5; ctx.strokeStyle = '#007bff';
    const lo = slitAnimationProgress < 1 ? curO : maxO;
    ctx.beginPath(); ctx.arc(0,0,domeRadius,-Math.PI/2-base-lo,-Math.PI/2-lo); ctx.stroke();
    ctx.beginPath(); ctx.arc(0,0,domeRadius,-Math.PI/2+lo,-Math.PI/2+base+lo); ctx.stroke();

    ctx.restore();

    // ── TELESCOPIO ────────────────────────────────────────────────────────────
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate((telescopeDeg * Math.PI) / 180);

    const tiltFactor    = Math.cos((telescopeTiltDeg * Math.PI) / 180);
    const dynamicLength = 15 + 29 * tiltFactor;
    const yOffset       = -dynamicLength / 2 - 4;

    ctx.fillStyle = '#ddeeff'; ctx.strokeStyle = '#333333'; ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.rect(-16, yOffset, 32, dynamicLength);
    ctx.fill(); ctx.stroke();

    ctx.fillStyle = '#cbd5e1';
    ctx.fillRect(-22, -8, 6, 16);
    ctx.fillRect( 16, -8, 6, 16);

    ctx.fillStyle = '#333333';
    ctx.fillRect(-10, yOffset - 4, 20, 4);

    ctx.beginPath();
    ctx.arc(0, 0, 3, 0, 2 * Math.PI);
    ctx.fillStyle = '#333333'; 
    ctx.fill();

    ctx.beginPath();
    ctx.moveTo(-4, yOffset - 10);
    ctx.lineTo( 4, yOffset - 10);
    ctx.lineTo( 0, yOffset - 18);
    ctx.closePath();
    ctx.fillStyle = varColor('--accent-color', '#007bff'); ctx.fill();

    ctx.restore();
}

function varColor(name, fallback) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
