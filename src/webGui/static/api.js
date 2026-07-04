// ═══════════════════════════════════════════════════════════════════════════════
//  api.js  —  interfaccia completa con l'osservatorio reale tramite Flask
//  Responsabilità:
//    • comunicazione HTTP con Flask / cmd_handler.py
//    • stato reale dell'osservatorio (aggiornato via polling, sarebbe bello in futuro usare i Web socket
//      per rendere il tutto più leggero, si perde il 'movimento real time' della cupola e telescopio)
//    • comandi di alto livello verso i moduli (GOTO, MOVE, GET, ...)
//    • callback onStateUpdate per notificare canvas.js dei cambiamenti
// ═══════════════════════════════════════════════════════════════════════════════

import { KEYS, POLL_KEYS } from "/webGuiStatic/Keys.js";

const serverIP   = window.location.hostname;
const serverPort = window.location.port; 


const FLASK_BASE = `http://${serverIP}:${serverPort}`; //<- IP del server

 
export const POLLING_PERIOD_MS = 10000;
// ────────────────────────────────────── Stato reale dell'osservatorio ──────────────────────────────────────
export const state = {
    domeDeg:          0,
    telescopeDeg:     0,
    telescopeTiltDeg: 0,
    isSlitOpen:       false,
};

// Callback registrata da canvas.js per ricevere aggiornamenti di stato
let _onStateUpdate = null;
export function onStateUpdate(callback) {
    _onStateUpdate = callback;
}


let _onTerminalUpdate = null;
export function onTerminalUpdate(callback) {
    _onTerminalUpdate = callback;
}


// ────────────────────────────────────── Primitive HTTP ──────────────────────────────────────
 
// Invia un comando testuale al cmd_parser Python
export async function sendCommand(commandText) {
    const res = await fetch(`${FLASK_BASE}/api/terminal`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ command: commandText })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
}
 
// Attende e restituisce la risposta prodotta da cmd_handler
export async function fetchResponse() {
    const res = await fetch(`${FLASK_BASE}/api/terminal`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.responses ?? [];
}
 
// Invia un comando e restituisce la risposta (shorthand usato da terminal.js)
export async function sendAndReceive(commandText) {
    await sendCommand(commandText);
    return await fetchResponse(); 
}// ────────────────────────────────────── Comandi di alto livello ─────────────────────────────────────────────────
 
// GOTO: muove cupola e telescopio verso gli angoli indicati
//   horizontal: azimut cupola (0-360)
//   vertical:   elevazione telescopio (0-180)
export async function gotoPosition(horizontal, vertical) {
    const h = Math.round(horizontal);
    const v = Math.round(vertical);
    return await sendAndReceive(`GOTO ${h} ${v}`);
}
 
// MOVE: invia comandi specifici a uno o più moduli
//   Esempio: moveModule('dome', ['45', 'ticks', 'absolute'])
//            moveModule('slit', ['open'])
export async function moveModule(moduleName, params) {
    const paramStr = params.join(',');
    return await sendAndReceive(`MOVE ${moduleName}:${paramStr}`);
}
 
// GET: legge chiavi di stato da uno o più moduli
//   Esempio: getModuleState({ dome: ['currentPositionInDeg'], telescope: ['horizontal','vertical'] })
export async function getModuleState(moduleKeys) {
    const query = Object.entries(moduleKeys)
        .map(([mod, keys]) => `${mod}:${keys.join(',')}`)
        .join(' ');
    return await sendAndReceive(`GET ${query}`);
}
 


function parseStateResponse(raw) {
    try {
        const data = JSON.parse(raw);

        // Gestione del modulo 'dome'
        if (data.dome) {
            if (KEYS.dome.currentPositionInDegrees in data.dome) {
                state.domeDeg = parseFloat(data.dome[KEYS.dome.currentPositionInDegrees]); 
            }
        }

        // Gestione del modulo 'telescope'
        if (data.telescope) {
            const tel = data.telescope;
            
            if (KEYS.telescope.horizontal in tel) {
                const v = parseFloat(tel.horizontal);
                if (!isNaN(v)) state.telescopeDeg = v;
            }
            if (KEYS.telescope.vertical in tel) {
                const v = parseFloat(tel.vertical);
                if (!isNaN(v)) state.telescopeTiltDeg = v;
            }
            if (KEYS.telescope.isOpen in tel) {
                if (typeof tel.isOpen === 'boolean') {
                    state.isSlitOpen = tel.isOpen;
                } else {
                    state.isSlitOpen = String(tel.isOpen).trim().toLowerCase() === 'true';
                }
            }
        }
    } catch (e) {
        console.error("Errore nel parsing del JSON:", e);
    }
}
 
// ─── Polling stato reale ─────────────────────────────────────────────────────
// Interroga il backend ogni `intervalMs` ms e aggiorna state{}.
export function startPolling(intervalMs = POLLING_PERIOD_MS) {
    async function poll() {
        try {
            const responses = await getModuleState(POLL_KEYS);
            for (const raw of responses) {
                if (!raw) continue;
                if (_onTerminalUpdate) _onTerminalUpdate(raw);
                try {
                    JSON.parse(raw);         // controlla se è JSON valido
                    parseStateResponse(raw); // elabora solo se lo è
                } catch (_) {
                    // non è JSON, ignora silenziosamente
                }
            }
            if (responses.length > 0 && _onStateUpdate) {
                _onStateUpdate({ ...state });
            }
        } catch (_) {}
    }
    poll();
    setInterval(poll, intervalMs);
}
