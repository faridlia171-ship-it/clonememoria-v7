
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

