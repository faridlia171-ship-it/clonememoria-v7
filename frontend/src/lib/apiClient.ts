class APIClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
  }

  private async request(path: string, options: RequestInit = {}) {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  }

  async get(path: string) {
    return this.request(path, { method: "GET" });
  }

  async post(path: string, body: any) {
    return this.request(path, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  async patch(path: string, body: any) {
    return this.request(path, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  async updateConsent(consents: any) {
    return this.patch("/users/consent", consents);
  }
}

export const apiClient = new APIClient();
