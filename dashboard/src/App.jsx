// dashboard/src/App.jsx
import { useEffect, useMemo, useState } from "react";
import {
  getReviewQueue,
  getReviewCase,
  postReviewAction,
  getMonitoringSummary,
  getMonitoringBuckets,
  getMonitoringTopMerchants,
} from "./api";

function Badge({ children }) {
  return (
    <span className="inline-flex items-center rounded-full border px-2 py-0.5 text-xs bg-white">
      {children}
    </span>
  );
}

function Card({ title, children }) {
  return (
    <div className="rounded-2xl border bg-white p-4 shadow-sm">
      <div className="mb-3 text-sm font-semibold text-gray-700">{title}</div>
      {children}
    </div>
  );
}

function fmt(n) {
  if (n === null || n === undefined) return "-";
  if (typeof n === "number") return n.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
  return String(n);
}

export default function App() {
  // Tabs
  const [tab, setTab] = useState("review"); // "review" | "monitoring"

  // Review state
  const [queue, setQueue] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [caseData, setCaseData] = useState(null);
  const [loadingQueue, setLoadingQueue] = useState(false);
  const [loadingCase, setLoadingCase] = useState(false);

  // Monitoring state
  const [monLoading, setMonLoading] = useState(false);
  const [mon, setMon] = useState({ summary: null, buckets: [], merchants: [] });

  // Shared
  const [error, setError] = useState("");
  const [analyst, setAnalyst] = useState("andre");
  const [notes, setNotes] = useState("");

  async function refreshQueue() {
    setLoadingQueue(true);
    setError("");
    try {
      const data = await getReviewQueue(100, 0);
      setQueue(data);

      if (!selectedId && data.length) setSelectedId(data[0].transaction_id);

      // If the selected case disappears from queue, auto-select first or clear.
      if (selectedId && !data.find((x) => x.transaction_id === selectedId)) {
        setSelectedId(data.length ? data[0].transaction_id : null);
        setCaseData(null);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoadingQueue(false);
    }
  }

  async function loadCase(id) {
    if (!id) return;
    setLoadingCase(true);
    setError("");
    try {
      const data = await getReviewCase(id);
      setCaseData(data);
    } catch (e) {
      setError(e.message);
      setCaseData(null);
    } finally {
      setLoadingCase(false);
    }
  }

  async function loadMonitoring() {
    setMonLoading(true);
    setError("");
    try {
      const [summary, buckets, merchants] = await Promise.all([
        getMonitoringSummary(),
        getMonitoringBuckets(),
        getMonitoringTopMerchants(10),
      ]);
      setMon({ summary, buckets, merchants });
    } catch (e) {
      setError(e.message);
    } finally {
      setMonLoading(false);
    }
  }

  // Auto-refresh the review queue every 5s (only when on review tab)
  useEffect(() => {
    refreshQueue();
    const t = setInterval(() => {
      if (tab === "review") refreshQueue();
    }, 5000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  // Load selected case when selection changes (review tab)
  useEffect(() => {
    if (tab === "review" && selectedId) loadCase(selectedId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, tab]);

  const reasons = useMemo(() => {
    const r = caseData?.assessment?.reasons;
    if (!r) return [];
    if (Array.isArray(r)) return r;
    try {
      return JSON.parse(r);
    } catch {
      return [];
    }
  }, [caseData]);

  async function act(action) {
    if (!selectedId) return;
    setError("");
    try {
      await postReviewAction(selectedId, action, analyst, notes || null);
      setNotes("");
      await refreshQueue();
      if (selectedId) await loadCase(selectedId);
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-7xl p-6">
        <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="text-2xl font-bold text-gray-900">Fraud Platform</div>
            <div className="text-sm text-gray-600">
              Human review queue + explainable scoring + monitoring
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setTab("review")}
              className={`rounded-xl border px-3 py-2 text-sm ${
                tab === "review"
                  ? "bg-gray-900 text-white"
                  : "bg-white hover:bg-gray-100"
              }`}
            >
              Review
            </button>

            <button
              onClick={() => {
                setTab("monitoring");
                loadMonitoring();
              }}
              className={`rounded-xl border px-3 py-2 text-sm ${
                tab === "monitoring"
                  ? "bg-gray-900 text-white"
                  : "bg-white hover:bg-gray-100"
              }`}
            >
              Monitoring
            </button>

            {tab === "review" ? (
              <button
                onClick={refreshQueue}
                className="rounded-xl border bg-white px-3 py-2 text-sm hover:bg-gray-100"
              >
                {loadingQueue ? "Refreshing..." : "Refresh"}
              </button>
            ) : (
              <button
                onClick={loadMonitoring}
                className="rounded-xl border bg-white px-3 py-2 text-sm hover:bg-gray-100"
              >
                {monLoading ? "Loading..." : "Refresh"}
              </button>
            )}

            <a
              className="rounded-xl border bg-white px-3 py-2 text-sm hover:bg-gray-100"
              href="http://127.0.0.1:8000/docs"
              target="_blank"
              rel="noreferrer"
            >
              API Docs
            </a>
          </div>
        </div>

        {error ? (
          <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            {error}
          </div>
        ) : null}

        {tab === "review" ? (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            {/* Queue */}
            <div className="lg:col-span-1">
              <Card title={`Review Queue (${queue.length})`}>
                <div className="max-h-[70vh] overflow-auto rounded-xl border bg-white">
                  {queue.length === 0 ? (
                    <div className="p-4 text-sm text-gray-600">
                      No manual reviews right now.
                    </div>
                  ) : (
                    <table className="w-full text-left text-sm">
                      <thead className="sticky top-0 bg-white">
                        <tr className="border-b">
                          <th className="p-3">Risk</th>
                          <th className="p-3">Amount</th>
                          <th className="p-3">Merchant</th>
                        </tr>
                      </thead>
                      <tbody>
                        {queue.map((row) => (
                          <tr
                            key={row.transaction_id}
                            className={`cursor-pointer border-b hover:bg-gray-50 ${
                              selectedId === row.transaction_id ? "bg-gray-100" : ""
                            }`}
                            onClick={() => setSelectedId(row.transaction_id)}
                          >
                            <td className="p-3">
                              <div className="font-semibold">{row.risk_score}</div>
                              <div className="text-xs text-gray-500">
                                {fmt(row.fraud_probability)}
                              </div>
                            </td>
                            <td className="p-3">
                              <div className="font-medium">{fmt(row.amount)}</div>
                              <div className="text-xs text-gray-500">{row.country}</div>
                            </td>
                            <td className="p-3">
                              <div className="font-medium">{row.merchant}</div>
                              <div className="text-xs text-gray-500">{row.user_id}</div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </Card>
            </div>

            {/* Case Details */}
            <div className="lg:col-span-2">
              <Card title="Case Details">
                {!selectedId ? (
                  <div className="text-sm text-gray-600">
                    Select a transaction from the queue.
                  </div>
                ) : loadingCase ? (
                  <div className="text-sm text-gray-600">Loading case...</div>
                ) : !caseData ? (
                  <div className="text-sm text-gray-600">No case data.</div>
                ) : (
                  <div className="space-y-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge>TX: {caseData.transaction.transaction_id}</Badge>
                      <Badge>User: {caseData.transaction.user_id}</Badge>
                      <Badge>Device: {caseData.transaction.device_id}</Badge>
                      <Badge>Card: {caseData.transaction.card_id}</Badge>
                    </div>

                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                      <div className="rounded-xl border p-3">
                        <div className="text-xs text-gray-500">Transaction</div>
                        <div className="mt-2 space-y-1 text-sm">
                          <div>
                            <span className="text-gray-500">Amount:</span>{" "}
                            {fmt(caseData.transaction.amount)} {caseData.transaction.currency}
                          </div>
                          <div>
                            <span className="text-gray-500">Merchant:</span>{" "}
                            {caseData.transaction.merchant} (
                            {caseData.transaction.merchant_category})
                          </div>
                          <div>
                            <span className="text-gray-500">Country:</span>{" "}
                            {caseData.transaction.country}
                          </div>
                          <div>
                            <span className="text-gray-500">Time:</span>{" "}
                            {caseData.transaction.timestamp}
                          </div>
                        </div>
                      </div>

                      <div className="rounded-xl border p-3">
                        <div className="text-xs text-gray-500">Model Decision</div>
                        <div className="mt-2 space-y-1 text-sm">
                          <div>
                            <span className="text-gray-500">Decision:</span>{" "}
                            <span className="font-semibold">
                              {caseData.assessment?.decision}
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-500">Risk score:</span>{" "}
                            <span className="font-semibold">
                              {caseData.assessment?.risk_score}
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-500">Fraud prob:</span>{" "}
                            {fmt(caseData.assessment?.fraud_probability)}
                          </div>
                        </div>

                        <div className="mt-3">
                          <div className="text-xs text-gray-500">Top reasons</div>
                          <div className="mt-2 space-y-2">
                            {reasons.length === 0 ? (
                              <div className="text-sm text-gray-600">
                                No reasons available.
                              </div>
                            ) : (
                              reasons.map((r, idx) => (
                                <div
                                  key={idx}
                                  className="rounded-lg border bg-gray-50 p-2 text-sm"
                                >
                                  <div className="font-medium">{r.feature}</div>
                                  <div className="text-xs text-gray-600">
                                    value={fmt(r.value)} · contribution={fmt(r.contribution)}
                                  </div>
                                </div>
                              ))
                            )}
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                      <div className="rounded-xl border p-3">
                        <div className="text-xs text-gray-500">Key Features</div>
                        <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
                          {caseData.features ? (
                            Object.entries(caseData.features)
                              .filter(([k]) => !["transaction_id", "created_at"].includes(k))
                              .slice(0, 10)
                              .map(([k, v]) => (
                                <div key={k} className="rounded-lg border bg-white p-2">
                                  <div className="text-xs text-gray-500">{k}</div>
                                  <div className="font-medium">
                                    {typeof v === "boolean" ? String(v) : fmt(v)}
                                  </div>
                                </div>
                              ))
                          ) : (
                            <div className="text-sm text-gray-600">No features found.</div>
                          )}
                        </div>
                      </div>

                      <div className="rounded-xl border p-3">
                        <div className="text-xs text-gray-500">Analyst Action</div>
                        <div className="mt-2 space-y-2">
                          <label className="block text-sm">
                            <span className="text-gray-600">Analyst</span>
                            <input
                              className="mt-1 w-full rounded-xl border px-3 py-2"
                              value={analyst}
                              onChange={(e) => setAnalyst(e.target.value)}
                            />
                          </label>

                          <label className="block text-sm">
                            <span className="text-gray-600">Notes</span>
                            <textarea
                              className="mt-1 w-full rounded-xl border px-3 py-2"
                              rows={3}
                              value={notes}
                              onChange={(e) => setNotes(e.target.value)}
                              placeholder="Why approve/reject?"
                            />
                          </label>

                          <div className="flex gap-2">
                            <button
                              onClick={() => act("approve")}
                              className="flex-1 rounded-xl border bg-white px-3 py-2 text-sm font-semibold hover:bg-gray-100"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => act("reject")}
                              className="flex-1 rounded-xl bg-gray-900 px-3 py-2 text-sm font-semibold text-white hover:bg-black"
                            >
                              Reject
                            </button>
                          </div>

                          <div className="mt-3">
                            <div className="text-xs text-gray-500">Review history</div>
                            <div className="mt-2 max-h-40 overflow-auto rounded-xl border bg-white">
                              {(caseData.review_history || []).length === 0 ? (
                                <div className="p-3 text-sm text-gray-600">
                                  No actions yet.
                                </div>
                              ) : (
                                <ul className="divide-y">
                                  {caseData.review_history.map((h) => (
                                    <li key={h.id} className="p-3 text-sm">
                                      <div className="flex items-center justify-between">
                                        <span className="font-semibold">{h.action}</span>
                                        <span className="text-xs text-gray-500">
                                          {h.created_at}
                                        </span>
                                      </div>
                                      <div className="text-xs text-gray-600">by {h.analyst}</div>
                                      {h.notes ? (
                                        <div className="mt-1 text-sm">{h.notes}</div>
                                      ) : null}
                                    </li>
                                  ))}
                                </ul>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </Card>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <Card title="Last 24h Decisions">
              {mon.summary ? (
                <div className="space-y-2 text-sm">
                  <div>
                    Total: <b>{mon.summary.total}</b>
                  </div>
                  <div>
                    Approve: <b>{mon.summary.approve}</b>
                  </div>
                  <div>
                    Manual review: <b>{mon.summary.manual_review}</b>
                  </div>
                  <div>
                    Block: <b>{mon.summary.block}</b>
                  </div>
                </div>
              ) : (
                <div className="text-sm text-gray-600">{monLoading ? "Loading..." : "No data."}</div>
              )}
            </Card>

            <Card title="Risk Score Buckets (24h)">
              {monLoading && mon.buckets.length === 0 ? (
                <div className="text-sm text-gray-600">Loading...</div>
              ) : (
                <div className="space-y-2 text-sm">
                  {mon.buckets.map((b) => (
                    <div
                      key={b.bucket}
                      className="flex items-center justify-between rounded-lg border bg-gray-50 p-2"
                    >
                      <span>{b.bucket}</span>
                      <b>{b.count}</b>
                    </div>
                  ))}
                  {mon.buckets.length === 0 ? (
                    <div className="text-sm text-gray-600">No bucket data yet.</div>
                  ) : null}
                </div>
              )}
            </Card>

            <Card title="Top Merchants by Avg Risk (24h)">
              {monLoading && mon.merchants.length === 0 ? (
                <div className="text-sm text-gray-600">Loading...</div>
              ) : (
                <div className="space-y-2 text-sm">
                  {mon.merchants.map((m) => (
                    <div key={m.merchant} className="rounded-lg border p-2">
                      <div className="font-semibold">{m.merchant}</div>
                      <div className="text-xs text-gray-600">
                        tx={m.tx_count} · avg_risk={typeof m.avg_risk === "number" ? m.avg_risk.toFixed(1) : m.avg_risk} · reviews={m.reviews} · blocks={m.blocks}
                      </div>
                    </div>
                  ))}
                  {mon.merchants.length === 0 ? (
                    <div className="text-sm text-gray-600">No merchant data yet.</div>
                  ) : null}
                </div>
              )}
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
