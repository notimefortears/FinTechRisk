const API_BASE = "http://127.0.0.1:8000";

async function req(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  if (!res.ok) {
    throw new Error(typeof data === "string" ? data : JSON.stringify(data));
  }
  return data;
}

export function getReviewQueue(limit = 50, offset = 0) {
  return req(`/review/queue?limit=${limit}&offset=${offset}`);
}

export function getReviewCase(transactionId) {
  return req(`/review/case/${transactionId}`);
}

export function postReviewAction(transactionId, action, analyst, notes) {
  return req(`/review/case/${transactionId}/action`, {
    method: "POST",
    body: JSON.stringify({ action, analyst, notes }),
  });
}
export function getMonitoringSummary() {
  return req(`/monitoring/summary`);
}

export function getMonitoringBuckets() {
  return req(`/monitoring/score_buckets`);
}

export function getMonitoringTopMerchants(limit = 10) {
  return req(`/monitoring/top_merchants?limit=${limit}`);
}
