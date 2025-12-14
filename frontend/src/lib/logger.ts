// Simple logger compatible Next.js / Browser / Server
const logger = {
  info: (...args: any[]) => {
    if (typeof console !== "undefined") console.info("[INFO]", ...args);
  },
  error: (...args: any[]) => {
    if (typeof console !== "undefined") console.error("[ERROR]", ...args);
  },
  warn: (...args: any[]) => {
    if (typeof console !== "undefined") console.warn("[WARN]", ...args);
  },
};

export default logger;
