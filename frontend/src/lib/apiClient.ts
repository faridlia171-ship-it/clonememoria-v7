async request(path: string, method = "GET", body?: any) {
  const url = `${this.baseUrl}${path}`;

  const headers: any = {
    "Content-Type": "application/json",
  };

  const token = this.getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const options: RequestInit = {
    method,
    headers,
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  const res = await fetch(url, options);

  if (!res.ok) {
    logger.error("API Error", { path, status: res.status });
    throw new Error(`API error: ${res.status}`);
  }

  // Try JSON, fallback text
  try {
    return await res.json();
  } catch {
    return await res.text();
  }
}
