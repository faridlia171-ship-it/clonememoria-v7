type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogData {
  [key: string]: any;
}

class Logger {
  private isDevelopment: boolean;

  constructor() {
    this.isDevelopment = process.env.NODE_ENV === 'development';
  }

  private formatLog(event: string, level: LogLevel, data?: LogData): void {
    const timestamp = new Date().toISOString();
    const logEntry = {
      timestamp,
      level: level.toUpperCase(),
      event,
      ...data,
    };

    if (this.isDevelopment) {
      const color = this.getColorForLevel(level);
      console.group(`%c${event}`, `color: ${color}; font-weight: bold;`);
      console.log('Level:', level.toUpperCase());
      console.log('Time:', timestamp);
      if (data && Object.keys(data).length > 0) {
        console.log('Data:', data);
      }
      console.groupEnd();
    } else {
      console.log(JSON.stringify(logEntry));
    }
  }

  private getColorForLevel(level: LogLevel): string {
    switch (level) {
      case 'debug':
        return '#9E9E9E';
      case 'info':
        return '#2196F3';
      case 'warn':
        return '#FF9800';
      case 'error':
        return '#F44336';
      default:
        return '#000000';
    }
  }

  debug(event: string, data?: LogData): void {
    this.formatLog(event, 'debug', data);
  }

  info(event: string, data?: LogData): void {
    this.formatLog(event, 'info', data);
  }

  warn(event: string, data?: LogData): void {
    this.formatLog(event, 'warn', data);
  }

  error(event: string, data?: LogData): void {
    this.formatLog(event, 'error', data);
  }
}

export const logger = new Logger();

export function log(event: string, data?: LogData): void {
  logger.info(event, data);
}
