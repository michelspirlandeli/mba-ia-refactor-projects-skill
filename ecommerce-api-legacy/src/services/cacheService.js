// Cache em memória encapsulado (antes: objeto global mutável exportado por utils.js).
class CacheService {
    #store = new Map();

    set(key, value) {
        this.#store.set(key, value);
    }

    get(key) {
        return this.#store.get(key);
    }
}

module.exports = CacheService;
