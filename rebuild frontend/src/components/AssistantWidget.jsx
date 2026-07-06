import { useEffect, useMemo, useRef, useState } from "react";
import { Bot, Maximize2, MessageSquare, Minimize2, Pencil, Plus, Send, Trash2, UserRound, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";

const welcomeMessage = {
  role: "assistant",
  text: "Hi, I am Mabel, an AI assistant from SafeLife. How can I help you?",
  results: []
};

const quickPrompts = [
  "Find Robert Johnson",
  "Top CCU last 4 months",
  "How many leads last 3 months?"
];

function leadSubtitle(lead) {
  return [
    lead.status,
    lead.source && `Source: ${lead.source}`,
    lead.staff_name && `Staff: ${lead.staff_name}`,
    lead.updated_at && `Updated: ${String(lead.updated_at).slice(0, 10)}`
  ].filter(Boolean).join(" | ");
}

function sessionTime(session) {
  const value = session?.last_message_at || session?.updated_at || session?.created_at;
  if (!value) return "";
  const date = new Date(String(value).replace(" ", "T"));
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 10);
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}

export default function AssistantWidget({ pageTitle = "", route = "" }) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [messages, setMessages] = useState([welcomeMessage]);
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [lastResults, setLastResults] = useState([]);
  const inputRef = useRef(null);
  const scrollRef = useRef(null);

  const canSend = useMemo(() => input.trim() && !loading && !loadingHistory, [input, loading, loadingHistory]);

  useEffect(() => {
    if (!open) return;
    api.get("/chat/sessions").then((response) => {
      setSessions(response.data.sessions || []);
    }).catch(() => setSessions([]));
  }, [open]);

  useEffect(() => {
    if (!open) return;
    window.setTimeout(() => {
      inputRef.current?.focus();
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    }, 50);
  }, [open, messages.length, loading, loadingHistory]);

  function startNewChat() {
    setActiveSessionId(null);
    setMessages([welcomeMessage]);
    setLastResults([]);
    setInput("");
  }

  async function openSession(sessionId) {
    if (loading || loadingHistory || sessionId === activeSessionId) return;
    setLoadingHistory(true);
    try {
      const response = await api.get(`/chat/sessions/${sessionId}/messages`);
      const loadedMessages = response.data.messages || [];
      setActiveSessionId(response.data.session?.id || sessionId);
      setMessages(loadedMessages.length ? loadedMessages : [welcomeMessage]);
      const newestResults = [...loadedMessages].reverse().find((item) => item.results?.length)?.results || [];
      setLastResults(newestResults);
    } finally {
      setLoadingHistory(false);
    }
  }

  async function renameSession(session, event) {
    event.stopPropagation();
    const title = window.prompt("Rename chat", session.title || "New chat");
    if (!title?.trim()) return;
    const response = await api.patch(`/chat/sessions/${session.id}`, { title: title.trim() });
    setSessions((current) => current.map((item) => item.id === session.id ? response.data.session : item));
  }

  async function deleteSession(session, event) {
    event.stopPropagation();
    if (!window.confirm(`Delete "${session.title}" from your chat history?`)) return;
    await api.delete(`/chat/sessions/${session.id}`);
    setSessions((current) => current.filter((item) => item.id !== session.id));
    if (activeSessionId === session.id) startNewChat();
  }

  async function sendMessage(text = input) {
    const message = String(text || "").trim();
    if (!message || loading || loadingHistory) return;

    setInput("");
    setMessages((current) => [...current, { role: "user", text: message, results: [] }]);
    setLoading(true);

    try {
      const history = messages.slice(-8).map((item) => ({
        role: item.role,
        text: item.text,
        results: (item.results || []).slice(0, 4).map((lead) => ({ id: lead.id, name: lead.name }))
      }));
      const response = await api.post("/chat", {
        sessionId: activeSessionId,
        message,
        history,
        contextResults: lastResults.slice(0, 12).map((lead) => ({ id: lead.id, name: lead.name })),
        pageContext: { pageTitle, route }
      });
      if (response.data.sessionId) setActiveSessionId(response.data.sessionId);
      if (response.data.results?.length) setLastResults(response.data.results);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text: response.data.answer,
          results: response.data.results || [],
          total: response.data.total,
          intent: response.data.intent
        }
      ]);
      if (response.data.session) {
        setSessions((current) => {
          const withoutCurrent = current.filter((session) => session.id !== response.data.session.id);
          return [response.data.session, ...withoutCurrent];
        });
      }
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text: error.response?.data?.error || "I could not answer that right now. Try a name, phone, ID, report, source, staff, or date range.",
          results: []
        }
      ]);
    } finally {
      setLoading(false);
    }
  }

  function openLead(lead) {
    const targetUrl = lead.target?.targetUrl || `/view-leads?idSearch=${lead.id}`;
    const separator = targetUrl.includes("?") ? "&" : "?";
    navigate(`${targetUrl}${separator}globalSearch=true`);
    setOpen(false);
  }

  return (
    <>
      {!open && (
        <button className="assistant-fab" onClick={() => setOpen(true)} aria-label="Open SafeLife AI Assistant">
          <Bot size={34} />
        </button>
      )}

      {open && (
        <section className={`assistant-widget ${expanded ? "expanded" : ""}`} aria-label="SafeLife AI Assistant">
          <header className="assistant-widget-head">
            <button className="assistant-icon-button" onClick={() => setOpen(false)} aria-label="Close assistant">
              <X size={22} />
            </button>
            <span className="assistant-brand-avatar"><Bot size={28} /></span>
            <div>
              <h3>SafeLife AI Assistant</h3>
              <p>Active | Ask any CRM question</p>
            </div>
            <button className="assistant-new-button" onClick={startNewChat}><Plus size={17} /> New Chat</button>
            <button className="assistant-icon-button" onClick={() => setExpanded((value) => !value)} aria-label={expanded ? "Collapse assistant" : "Expand assistant"}>
              {expanded ? <Minimize2 size={22} /> : <Maximize2 size={22} />}
            </button>
          </header>

          <div className="assistant-widget-body">
            <aside className="assistant-session-list">
              <div className="assistant-session-title">Recent Chats</div>
              {sessions.length ? sessions.slice(0, 20).map((session) => (
                <button
                  className={`assistant-session-item ${activeSessionId === session.id ? "active" : ""}`}
                  key={session.id}
                  onClick={() => openSession(session.id)}
                  disabled={loadingHistory}
                >
                  <MessageSquare size={16} />
                  <span>
                    <strong>{session.title}</strong>
                    <small>{sessionTime(session)}</small>
                  </span>
                  <em>
                    <i title="Rename chat" onClick={(event) => renameSession(session, event)}><Pencil size={13} /></i>
                    <i title="Delete chat" onClick={(event) => deleteSession(session, event)}><Trash2 size={13} /></i>
                  </em>
                </button>
              )) : (
                <p>No chat history yet.</p>
              )}
            </aside>

            <div className="assistant-chat-area">
              <div className="assistant-messages" ref={scrollRef}>
                {loadingHistory ? (
                  <article className="assistant-message assistant">
                    <span><Bot size={18} /></span>
                    <div className="assistant-bubble loading">Loading chat history...</div>
                  </article>
                ) : messages.map((message, index) => (
                  <article className={`assistant-message ${message.role}`} key={message.id || `${message.role}-${index}`}>
                    <span>{message.role === "assistant" ? <Bot size={18} /> : <UserRound size={18} />}</span>
                    <div className="assistant-bubble">
                      <p>{message.text}</p>
                      {message.results?.length ? (
                        <div className="assistant-results">
                          {message.results.map((lead) => (
                            <button key={lead.id} onClick={() => openLead(lead)}>
                              <strong>ID {lead.id} | {lead.name}</strong>
                              <small>{leadSubtitle(lead)}</small>
                            </button>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  </article>
                ))}
                {loading && (
                  <article className="assistant-message assistant">
                    <span><Bot size={18} /></span>
                    <div className="assistant-bubble loading">Searching CRM data...</div>
                  </article>
                )}
              </div>

              <div className="assistant-quick-prompts">
                {quickPrompts.map((prompt) => (
                  <button key={prompt} onClick={() => sendMessage(prompt)} disabled={loading || loadingHistory}>{prompt}</button>
                ))}
              </div>

              <form className="assistant-input" onSubmit={(event) => { event.preventDefault(); sendMessage(); }}>
                <input
                  ref={inputRef}
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  placeholder="Ask about leads, referrals, reports, staff, CCU, source..."
                  maxLength={800}
                />
                <button type="submit" disabled={!canSend} aria-label="Send message"><Send size={19} /></button>
              </form>
            </div>
          </div>
        </section>
      )}
    </>
  );
}
