const fs = require('fs');

const NULL_IMAGE_TOKENS = new Set(['', 'nil', 'none', 'null', 'na', 'n/a', '(none)']);

const PT_PER_PX = 0.75;
const PX_PER_IN = 96;
const EMU_PER_IN = 914400;

function normalizeLocalPath(maybeUrlOrPath) {
    if (!maybeUrlOrPath) return null;
    const raw = String(maybeUrlOrPath).trim().replace(/^['"]|['"]$/g, '');
    if (NULL_IMAGE_TOKENS.has(raw.toLowerCase())) return null;
    return raw.startsWith('file://') ? raw.replace('file://', '') : raw;
}

function isReadableFile(filePath) {
    if (!filePath) return false;
    try {
        const stats = fs.statSync(filePath);
        return stats.isFile();
    } catch {
        return false;
    }
}

module.exports = {
    PT_PER_PX,
    PX_PER_IN,
    EMU_PER_IN,
    normalizeLocalPath,
    isReadableFile
};
