export const STORAGE_KEY = "research-catalyst:editor-v2:project";

export function loadFromStorage<T>(fallback: T, key = STORAGE_KEY): T {
    if (typeof window === "undefined") return fallback;
    try {
        const raw = window.localStorage.getItem(key);
        if (!raw) return fallback;
        return JSON.parse(raw) as T;
    } catch {
        return fallback;
    }
}

export function saveToStorage<T>(value: T, key = STORAGE_KEY): void {
    if (typeof window === "undefined") return;
    try {
        window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
        // localStorage quota or restricted mode
    }
}

