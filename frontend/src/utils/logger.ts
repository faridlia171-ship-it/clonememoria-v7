// src/utils/logger.ts
// Front-end safe logger — Option B hardened mode

type LogLevel = "debug" | "info" | "warn" | "error";

// Champs sensibles à filtrer systématiquement
const SENSITIVE_KEYS = ["password", "token", "refresh", "email", "authorization"];

// Fonction de filtrage profond
const sanitize = (data: any): any => {
    if (!data || typeof data !== "object") return data;

    const cleaned: any = Array.isArray(data) ? [] : {};

    for (const key of Object.keys(data)) {
        if (SENSITIVE_KEYS.includes(key.toLowerCase())) {
            cleaned[key] = "***REDACTED***";
        } else {
            cleaned[key] = sanitize(data[key]);
        }
    }
    return cleaned;
};

// Mode production = logs minimalistes
const isProd =
    typeof window !== "undefined" &&
    process.env.NODE_ENV === "production";

function baseLog(level: LogLevel, message: string, meta?: any) {
    const safeMeta = sanitize(meta);

    if (isProd) {
        // En production : log minimal
        console[level](`[${level.toUpperCase()}] ${message}`);
        return;
    }

    // En développement : log complet
    const timestamp = new Date().toISOString();
    const colors: Record<LogLevel, string> = {
        debug: "color: #7f8c8d",
        info: "color: #2980b9",
        warn: "color: #f39c12",
        error: "color: #c0392b"
    };

    console[level](
        `%c[${level.toUpperCase()}] ${timestamp} — ${message}`,
        colors[level],
        safeMeta || ""
    );
}

const logger = {
    debug: (msg: string, meta?: any) => baseLog("debug", msg, meta),
    info: (msg: string, meta?: any) => baseLog("info", msg, meta),
    warn: (msg: string, meta?: any) => baseLog("warn", msg, meta),
    error: (msg: string, meta?: any) => baseLog("error", msg, meta),
};

export default logger;
export { logger };
