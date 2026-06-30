// ═══════════════════════════════════════════════════════════════════════════════
//  terminal.js  —  UI del terminale
//  Responsabilità: rendering log, input utente, inoltro comandi ad api.js
// ═══════════════════════════════════════════════════════════════════════════════
import { sendAndReceive, onTerminalUpdate } from '/webGuiStatic/api.js';

// ────────────────────────────────────── Log ──────────────────────────────────────
export function logToTerminal(text, type = 'info') {
    const termLog = document.getElementById('termLog');
    if (!termLog) return;
    const msg  = document.createElement('div');
    const time = new Date().toLocaleTimeString();

    if (type === 'cmd') {
        msg.innerHTML = `<span style="color:#000000">&gt; ${text}</span>`;
    } else if (type === 'error') {
        msg.innerHTML = `[${time}] <span style="color:#cc0000">ERR: ${text}</span>`;
    } else if (type === 'resp') {
        const normalized = text.toUpperCase().replace(/\[\s*/g, '[').replace(/\s*\]/g, ']'); // toglie gli spazi tra le quadre e la scritta
        let color = '#0050cc';
       try {
            JSON.parse(text);
            color = '#888888'; // grigio se è JSON valido
        } catch (_) {
            if      (normalized.includes('[ERROR]'))   color = '#cc0000';
            else if (normalized.includes('[WARNING]')) color = '#ff8800';
            else if (normalized.includes('[INFO]'))    color = '#008800';
        }
        msg.style.whiteSpace = 'pre-wrap'; //fa rispettare sia spazi che '/n'
        msg.innerHTML = `[${time}] <span style="color:${color}">${text}</span>`;    
    } else {
        msg.innerHTML = `[${time}] ${text}`;
    }

    termLog.appendChild(msg);
    termLog.scrollTop = termLog.scrollHeight;
}

// ─── Init listener ───────────────────────────────────────────────────────────
// Chiamata da canvas.js dopo DOMContentLoaded
export function initTerminal() {
    onTerminalUpdate((text) => logToTerminal(text, 'resp'));
    const termInput = document.getElementById('termInput');
    const btnTerm   = document.getElementById('btnTerm');
 
    async function submitCommand() {
        const cmd = termInput.value.trim();
        if (!cmd) return;
        termInput.value = '';
        logToTerminal(cmd, 'cmd');
        try {
            const responses = await sendAndReceive(cmd);
            for (const r of responses) {
                if (!r) continue;
                logToTerminal(r, 'resp');       // stampa sempre tutto

                try {
                    const parsed = JSON.parse(r);
                    handleJsonResponse(parsed); // elabora solo se JSON
                } catch (_) {
                    // stringa normale, già stampata sopra
                }
            }
        } catch (e) {
            logToTerminal(`Connessione a Flask fallita: ${e.message}`, 'error');
        }
    }

    // elaborazione risposte JSON dal terminale (es. aggiornare la UI)
    function handleJsonResponse(parsed) {
        // per ora aggiorna lo stato della canvas se contiene dati dei moduli
        if (_onStateUpdate) _onStateUpdate(parsed);
    }
 
    if (btnTerm) btnTerm.addEventListener('click', submitCommand);
    termInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') submitCommand();
    });
}