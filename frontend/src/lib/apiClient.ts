// src/lib/apiClient.ts
import logger from "@/utils/logger";

class APIClient {
  constructor(private baseUrl: string) {}

  async request(path: string, method = "GET", body?: any) {
    const url = `${this.baseUrl}${path}`;

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    const token =
      typeof window !== "undefined"
        ? localStorage.getItem("token")
        : null;

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!res.ok) {
      const errorText = await res.text();
      logger.error("API error", { url, method, errorText });
      throw new Error(errorText);
    }

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

  put(path: string, body: any) {
    return this.request(path, "PUT", body);
  }

  delete(path: string) {
    return this.request(path, "DELETE");
  }

  // Consentement : pas de userId → backend récupère depuis token JWT
  updateConsent(consent: Record<string, boolean>) {
    return this.post(`/users/me/consent`, consent);
  }

  // Export données personnelles
  exportUserData() {
    return this.get(`/users/me/export`);
  }
}

const apiClient = new APIClient(
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:5600"
);

export default apiClient;
