// keys.js  —  unica fonte di verità per le chiavi dei moduli
// Modificare qui si propaga automaticamente a api.js e ovunque venga importato

export const KEYS = {
    dome: {
        currentPositionInDegrees: 'currentPosInDegrees',
        status:                   'status',
    },
    telescope: {
        horizontal: 'horizontal',
        vertical:   'vertical',
        isOpen:     'isOpen',
    },
    slit: {
        isOpen: 'isOpen',
    }
};

// Chiavi da richiedere nel polling — costruite dalle costanti sopra
export const POLL_KEYS = {
    dome:      [ KEYS.dome.currentPositionInDegrees ],
    telescope: [ KEYS.telescope.horizontal, KEYS.telescope.vertical, KEYS.telescope.isOpen ],
};