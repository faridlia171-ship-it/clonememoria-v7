import { logger } from './logger';

export class APIClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
  }

  private async request(method: string, path: string, body?: any) {
    const token = localStorage.getItem("token");

    const headers: any = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = Bearer ;

    const options: any = { method, headers };
    if (body) options.body = JSON.stringify(body);

    const res = await fetch(${this.baseUrl}, options);

    if (!res.ok) {
      logger.error("API Error", { path, status: res.status });
      throw new Error(API error: );
    }

    return res.json().catch(() => null);
  }

  // === User Consent ===
  async updateConsent(consents: any) {
    return this.request("PATCH", "/users/consent", consents);
  }

  // === Export User Data ===
  async exportUserData() {
    return this.request("GET", "/users/export");
  }
}

export const apiClient = new APIClient();
