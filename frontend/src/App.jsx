import {
  useEffect,
  useRef,
  useState,
} from "react";
import "./App.css";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000";

const TURNSTILE_SITE_KEY =
  import.meta.env.VITE_TURNSTILE_SITE_KEY;

function App() {
  const [review, setReview] = useState(null);
  const [trace, setTrace] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const turnstileContainerRef = useRef(null);
  const turnstileWidgetIdRef = useRef(null);

  const [turnstileToken, setTurnstileToken] =
    useState("");

  const [pendingData, setPendingData] = useState({
    count: 0,
    pending_runs: [],
  });

  const [pendingLoading, setPendingLoading] = useState(false);
  const [pendingError, setPendingError] = useState("");
  const [approvingRunId, setApprovingRunId] = useState(null);
  const [approvalMessage, setApprovalMessage] = useState("");
  const [activeSection, setActiveSection] = useState("overview");

  useEffect(() => {
    loadPendingApprovals();
  }, []);

  useEffect(() => {
    let cancelled = false;
    let retryTimer = null;

    if (!TURNSTILE_SITE_KEY) {
      setError(
        "Turnstile site key is missing. Check frontend/.env."
      );
      return undefined;
    }

    function renderTurnstile() {
      if (cancelled) {
        return;
      }

      if (
        window.turnstile &&
        turnstileContainerRef.current &&
        turnstileWidgetIdRef.current === null
      ) {
        turnstileWidgetIdRef.current =
          window.turnstile.render(
            turnstileContainerRef.current,
            {
              sitekey: TURNSTILE_SITE_KEY,

              callback: (token) => {
                setTurnstileToken(token);
              },

              "expired-callback": () => {
                setTurnstileToken("");
              },

              "error-callback": () => {
                setTurnstileToken("");
              },
            }
          );

        return;
      }

      retryTimer = setTimeout(
        renderTurnstile,
        200
      );
    }

    renderTurnstile();

    return () => {
      cancelled = true;

      if (retryTimer) {
        clearTimeout(retryTimer);
      }

      if (
        window.turnstile &&
        turnstileWidgetIdRef.current !== null
      ) {
        window.turnstile.remove(
          turnstileWidgetIdRef.current
        );

        turnstileWidgetIdRef.current = null;
      }
    };
  }, []);

  function scrollToSection(sectionId) {
    setActiveSection(sectionId);

    const section = document.getElementById(sectionId);

    if (section) {
      section.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  }

  async function generateDailyReview() {
    try {
      setLoading(true);
      setError("");

      if (!turnstileToken) {
        throw new Error(
          "Please complete the security check first."
        );
      }

      const response = await fetch(
        `${API_BASE}/pipeline/review`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            turnstile_token: turnstileToken,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Failed to generate daily review."
        );
      }

      setReview(data.review);
      setTrace(data.trace || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      setTurnstileToken("");

      if (
        window.turnstile &&
        turnstileWidgetIdRef.current !== null
      ) {
        window.turnstile.reset(
          turnstileWidgetIdRef.current
        );
      }
    }
  }

  async function loadPendingApprovals() {
    try {
      setPendingLoading(true);
      setPendingError("");

      const response = await fetch(
        `${API_BASE}/agent/pending`
      );

      if (!response.ok) {
        throw new Error(
          "Failed to load pending approvals."
        );
      }

      const data = await response.json();

      setPendingData({
        count: data.count || 0,
        pending_runs: data.pending_runs || [],
      });
    } catch (err) {
      setPendingError(err.message);
    } finally {
      setPendingLoading(false);
    }
  }

  async function approvePendingRun(run) {
    try {
      setApprovingRunId(run.run_id);
      setPendingError("");
      setApprovalMessage("");

      const response = await fetch(
        `${API_BASE}/agent/approve`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            run_id: run.run_id,
          }),
        }
      );

      if (!response.ok) {
        throw new Error(
          "Approval request failed."
        );
      }

      const data = await response.json();

      if (data.status !== "completed") {
        throw new Error(
          data.message || "Approval could not be completed."
        );
      }

      let message =
        "Approval completed. CRM write executed.";

      const customerId =
        run.approvals?.[0]?.arguments?.customer_id;

      if (customerId) {
        try {
          const customerResponse = await fetch(
            `${API_BASE}/customers/${customerId}`
          );

          if (customerResponse.ok) {
            const customer =
              await customerResponse.json();

            message =
              `Approved. ${customer.name} is now ` +
              `${customer.lead_status}.`;
          }
        } catch {
          // Approval already succeeded.
          // CRM verification message is optional.
        }
      }

      setApprovalMessage(message);

      await loadPendingApprovals();
    } catch (err) {
      setPendingError(err.message);
    } finally {
      setApprovingRunId(null);
    }
  }

  const crmAgentUsed = trace.some(
    (item) => item.specialist === "crm_specialist"
  );

  const researchAgentUsed = trace.some(
    (item) =>
      item.specialist === "research_specialist"
  );

  return (
    <div className="app">
      <aside className="sidebar">
        <div>
          <h2>AI Sales Copilot</h2>

          <p className="subtitle">
            Multi-Agent CRM Assistant
          </p>
        </div>

        <nav>
          <button
            type="button"
            className={
              activeSection === "overview"
                ? "nav-item active"
                : "nav-item"
            }
            onClick={() => scrollToSection("overview")}
          >
            Overview
          </button>

          <button
            type="button"
            className={
              activeSection === "pipeline"
                ? "nav-item active"
                : "nav-item"
            }
            onClick={() => scrollToSection("pipeline")}
          >
            Pipeline
          </button>

          <button
            type="button"
            className={
              activeSection === "ai-review"
                ? "nav-item active"
                : "nav-item"
            }
            onClick={() => scrollToSection("ai-review")}
          >
            AI Review
          </button>

          <button
            type="button"
            className={
              activeSection === "approvals"
                ? "nav-item active"
                : "nav-item"
            }
            onClick={() => scrollToSection("approvals")}
          >
            Approvals
          </button>

          <button
            type="button"
            className={
              activeSection === "agent-activity"
                ? "nav-item active"
                : "nav-item"
            }
            onClick={() =>
              scrollToSection("agent-activity")
            }
          >
            Agent Activity
          </button>
        </nav>

        <div className="sidebar-footer">
          OpenAI Agents SDK
        </div>
      </aside>

      <main className="main">
        <header className="header" id="overview">
          <div>
            <p className="eyebrow">
              SALES OPERATIONS
            </p>

            <h1>Good morning, Tiger</h1>

            <p className="description">
              Review your highest-priority
              opportunities and AI recommendations.
            </p>
          </div>

          <div>
            <div
              ref={turnstileContainerRef}
              style={{ marginBottom: "12px" }}
            />

            <button
              className="primary-button"
              onClick={generateDailyReview}
              disabled={loading || !turnstileToken}
            >
              {loading
                ? "Generating..."
                : "Generate Daily Review"}
            </button>
          </div>
        </header>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        <section className="stats-grid">
          <div className="stat-card">
            <span>Active Leads</span>
            <strong>4</strong>
            <small>CRM pipeline</small>
          </div>

          <div className="stat-card">
            <span>Top Priority</span>

            <strong>
              {review?.top_leads?.[0]?.name || "—"}
            </strong>

            <small>
              {review?.top_leads?.[0]
                ? `Lead score: ${review.top_leads[0].lead_score}`
                : "Generate review first"}
            </small>
          </div>

          <div className="stat-card">
            <span>AI Specialists</span>
            <strong>2</strong>
            <small>CRM + Research</small>
          </div>

          <div className="stat-card">
            <span>Pending Approvals</span>

            <strong>
              {pendingLoading
                ? "..."
                : pendingData.count}
            </strong>

            <small>Human-in-the-loop</small>
          </div>
        </section>

        <section className="approval-panel" id="approvals">
          <div className="approval-header">
            <div>
              <p className="eyebrow">
                HUMAN-IN-THE-LOOP
              </p>

              <h2>Pending Approvals</h2>
            </div>

            <div className="approval-count">
              {pendingData.count} pending
            </div>
          </div>

          {pendingError && (
            <div className="approval-error">
              {pendingError}
            </div>
          )}

          {approvalMessage && (
            <div className="approval-success">
              {approvalMessage}
            </div>
          )}

          {pendingLoading ? (
            <p className="empty-state">
              Loading pending approvals...
            </p>
          ) : pendingData.pending_runs.length > 0 ? (
            <div className="approval-list">
              {pendingData.pending_runs.map(
                (run) => (
                  <div
                    className="approval-card"
                    key={run.run_id}
                  >
                    <div className="approval-card-main">
                      {run.approvals.map(
                        (approval, index) => {
                          const customer =
                            approval.customer;

                          const newStatus =
                            approval.arguments
                              ?.new_status;

                          return (
                            <div
                              key={`${run.run_id}-${index}`}
                            >
                              <div className="approval-customer">
                                <div>
                                  <strong>
                                    {customer?.name ||
                                      "CRM Customer"}
                                  </strong>

                                  <span>
                                    {customer?.company ||
                                      "Unknown company"}
                                  </span>
                                </div>

                                <span className="approval-badge">
                                  Approval required
                                </span>
                              </div>

                              <div className="approval-action">
                                <span className="approval-action-label">
                                  CRM Status Change
                                </span>

                                <div className="status-change">
                                  <span className="status-old">
                                    {customer?.current_status ||
                                      "unknown"}
                                  </span>

                                  <span className="status-arrow">
                                    →
                                  </span>

                                  <span className="status-new">
                                    {newStatus ||
                                      "unknown"}
                                  </span>
                                </div>
                              </div>

                              <p className="approval-tool">
                                Tool:{" "}
                                <strong>
                                  {approval.tool}
                                </strong>
                              </p>
                            </div>
                          );
                        }
                      )}
                    </div>

                    <div className="approval-card-side">
                      <span className="durable-label">
                        Durable RunState
                      </span>

                      <button
                        className="approve-button"
                        onClick={() =>
                          approvePendingRun(run)
                        }
                        disabled={
                          approvingRunId ===
                          run.run_id
                        }
                      >
                        {approvingRunId ===
                        run.run_id
                          ? "Approving..."
                          : "Approve"}
                      </button>
                    </div>
                  </div>
                )
              )}
            </div>
          ) : (
            <div className="approval-empty">
              <strong>
                No actions awaiting approval
              </strong>

              <span>
                AI-initiated CRM writes will appear
                here before execution.
              </span>
            </div>
          )}
        </section>

        <section className="content-grid">
          <div className="panel" id="pipeline">
            <p className="eyebrow">
              TODAY'S PIPELINE
            </p>

            <h2>Top Leads</h2>

            {review ? (
              review.top_leads.map(
                (lead, index) => (
                  <div
                    className="lead-row"
                    key={lead.customer_id}
                  >
                    <div className="rank">
                      {index + 1}
                    </div>

                    <div className="lead-info">
                      <strong>
                        {lead.name}
                      </strong>

                      <span>
                        {lead.company}
                      </span>

                      <p className="lead-reason">
                        {lead.crm_reason}
                      </p>
                    </div>

                    <div className="score">
                      {lead.lead_score}
                    </div>
                  </div>
                )
              )
            ) : (
              <p className="empty-state">
                Generate a daily review to load
                live pipeline priorities.
              </p>
            )}
          </div>

          <div className="panel" id="agent-activity">
            <p className="eyebrow">
              MULTI-AGENT WORKFLOW
            </p>

            <h2>Agent Activity</h2>

            <div className="agent-flow">
              <div className="agent-box">
                <strong>Sales Manager</strong>
                <span>Orchestrator</span>
              </div>

              <div className="flow-arrow">
                ↓
              </div>

              <div className="specialists">
                <div
                  className={
                    crmAgentUsed
                      ? "agent-box agent-active"
                      : "agent-box"
                  }
                >
                  <strong>
                    CRM Specialist
                  </strong>

                  <span>
                    {crmAgentUsed
                      ? "Completed"
                      : "Waiting"}
                  </span>
                </div>

                <div
                  className={
                    researchAgentUsed
                      ? "agent-box agent-active"
                      : "agent-box"
                  }
                >
                  <strong>
                    Research Specialist
                  </strong>

                  <span>
                    {researchAgentUsed
                      ? "Completed"
                      : "Waiting"}
                  </span>
                </div>
              </div>

              <div className="flow-arrow">
                ↓
              </div>

              <div className="agent-box">
                <strong>
                  Recommendation
                </strong>

                <span>
                  {review
                    ? "Ready"
                    : "Waiting"}
                </span>
              </div>
            </div>
          </div>
        </section>

        <section className="detail-grid" id="ai-review">
          <div className="panel">
            <p className="eyebrow">
              EXTERNAL INTELLIGENCE
            </p>

            <h2>Buying Signals</h2>

            {review?.buying_signals?.length ? (
              review.buying_signals.map(
                (signal, index) => (
                  <div
                    className="signal-card"
                    key={`${signal.company}-${index}`}
                  >
                    <div className="signal-header">
                      <strong>
                        {signal.company}
                      </strong>

                      <span>
                        Verified signal
                      </span>
                    </div>

                    <p className="signal-fact">
                      {signal.verified_fact}
                    </p>

                    <p className="signal-interpretation">
                      <strong>
                        Sales interpretation:
                      </strong>{" "}
                      {signal.sales_interpretation}
                    </p>

                    <p className="signal-source">
                      Source: {signal.source}
                    </p>
                  </div>
                )
              )
            ) : (
              <p className="empty-state">
                Generate a review to research
                current buying signals.
              </p>
            )}
          </div>

          <div className="panel">
            <p className="eyebrow">
              AI RECOMMENDATIONS
            </p>

            <h2>Recommended Actions</h2>

            {review?.action_items?.length ? (
              <div className="action-list">
                {review.action_items.map(
                  (action, index) => (
                    <div
                      className="action-item"
                      key={index}
                    >
                      <div className="action-number">
                        {index + 1}
                      </div>

                      <p>{action}</p>
                    </div>
                  )
                )}
              </div>
            ) : (
              <p className="empty-state">
                Generate a review to create
                prioritized next actions.
              </p>
            )}
          </div>
        </section>

        {review?.warnings?.length > 0 && (
          <section className="warning-panel">
            <div>
              <p className="eyebrow">
                RELIABILITY
              </p>

              <h2>
                AI Safety & Data Notes
              </h2>
            </div>

            <ul>
              {review.warnings.map(
                (warning, index) => (
                  <li key={index}>
                    {warning}
                  </li>
                )
              )}
            </ul>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;