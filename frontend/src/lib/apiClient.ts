import logger from "./logger";

class APIClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:5001";
  }

  async request(path: string, method = "GET", body?: any) {
    const url = `${this.baseUrl}${path}`;

    const headers: any = {
      "Content-Type": "application/json",
    };

    const options: any = { method, headers };
    if (body) options.body = JSON.stringify(body);

    const res = await fetch(url, options);

    if (!res.ok) {
      logger.error("API Error", { path, status: res.status });
      throw new Error(`API request failed: ${res.status}`);
    }

    try {
      return await res.json();
    } catch {
      return await res.text();
    }
  }

  // ----------------------
  // Auth
  // ----------------------
  async login(data: any) {
    return this.request("/auth/login", "POST", data);
  }

  async register(data: any) {
    return this.request("/auth/register", "POST", data);
  }

  async getProfile() {
    return this.request("/users/me");
  }

  async exportUserData() {
    return this.request("/users/export");
  }

  async updateConsent(consents: any) {
    return this.request("/users/consent", "PATCH", consents);
  }
}

const apiClient = new APIClient();
export default apiClient;
