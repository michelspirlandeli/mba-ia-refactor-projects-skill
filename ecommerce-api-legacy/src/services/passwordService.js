const crypto = require('crypto');
const { promisify } = require('util');

const scrypt = promisify(crypto.scrypt);
const KEY_LENGTH = 64;
const SALT_BYTES = 16;

// Hash de senha com scrypt + salt aleatório (substitui o "badCrypto" baseado em base64).
async function hash(password) {
    const salt = crypto.randomBytes(SALT_BYTES).toString('hex');
    const derived = await scrypt(password, salt, KEY_LENGTH);
    return `${salt}:${derived.toString('hex')}`;
}

async function verify(password, stored) {
    const [salt, expected] = String(stored).split(':');
    if (!salt || !expected) return false;
    const expectedBuf = Buffer.from(expected, 'hex');
    if (expectedBuf.length !== KEY_LENGTH) return false;
    const derived = await scrypt(password, salt, KEY_LENGTH);
    return crypto.timingSafeEqual(expectedBuf, derived);
}

module.exports = { hash, verify };
