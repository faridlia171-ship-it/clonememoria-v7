import logger from "./logger";

export default class APIClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  setToken(token: string | null) {
    this.token = token;
  }

  // -----------------------------------------------------
  // REQUEST GENERIQUE
  // -----------------------------------------------------
  async request(path: string, method = "GET", body?: any) {
    const url = `${this.baseUrl}${path}`;

    const headers: any = {
      "Content-Type": "application/json",
    };
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    const options: any = { method, headers };
    if (body) options.body = JSON.stringify(body);

    const res = await fetch(url, options);

    if (!res.ok) {
      logger.error("API Error", { path, status: res.status });
      throw new Error(`API Error: ${res.status}`);
    }

    // Try JSON, fallback text
    try {
      return await res.json();
    } catch {
      return await res.text();
    }
  }

  get(path: string) {
    return this.request(path, "GET");
  }

  post(path: string, body: any) {
    return this.request(path, "POST", body);
  }

  patch(path: string, body: any) {
    return this.request(path, "PATCH", body);
  }

  delete(path: string) {
    return this.request(path, "DELETE");
  }

  // -----------------------------------------------------
  // METHODES UTILISATEUR
  // -----------------------------------------------------
  async updateConsent(consents: any) {
    return this.patch("/users/consent", consents);
  }

  async exportUserData() {
    return this.get("/users/export");
  }
}
