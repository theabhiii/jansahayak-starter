from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/debug", tags=["debug"])

_MAX_EVENTS = 120
_events: deque[dict[str, Any]] = deque(maxlen=_MAX_EVENTS)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _truncate(value: str, limit: int = 6000) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit]}\n\n... truncated ..."


def _summarize_headers(headers: dict[str, str]) -> dict[str, str]:
    allowed = {
        "content-type",
        "content-length",
        "user-agent",
        "x-forwarded-for",
        "x-forwarded-host",
        "x-forwarded-proto",
        "x-twilio-signature",
        "host",
    }
    return {k: v for k, v in headers.items() if k.lower() in allowed}


def _summarize_body(body: bytes, content_type: str) -> str:
    if not body:
        return ""

    lowered = (content_type or "").lower()
    text = body.decode("utf-8", errors="replace")
    if "application/json" in lowered:
        try:
            return _truncate(json.dumps(json.loads(text), indent=2, ensure_ascii=False))
        except Exception:
            return _truncate(text)
    return _truncate(text)


def record_event(
    *,
    method: str,
    path: str,
    query_string: str,
    request_headers: dict[str, str],
    request_body: bytes,
    response_status: int,
    response_headers: dict[str, str],
    response_body: bytes,
    duration_ms: float,
) -> None:
    request_content_type = request_headers.get("content-type", "")
    response_content_type = response_headers.get("content-type", "")
    _events.appendleft(
        {
            "id": uuid4().hex,
            "created_at": _utc_now_iso(),
            "method": method,
            "path": path,
            "query_string": query_string,
            "duration_ms": round(duration_ms, 1),
            "request": {
                "headers": _summarize_headers(request_headers),
                "content_type": request_content_type,
                "body": _summarize_body(request_body, request_content_type),
            },
            "response": {
                "status_code": response_status,
                "headers": _summarize_headers(response_headers),
                "content_type": response_content_type,
                "body": _summarize_body(response_body, response_content_type),
            },
        }
    )


@router.get("/inspector")
def inspector_page() -> HTMLResponse:
    html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>JanSahayak Inspector</title>
  <style>
    :root {
      --bg: #f5f2ea;
      --panel: rgba(255,255,255,0.82);
      --line: #d5d0c3;
      --text: #1d1a16;
      --muted: #6b655b;
      --brand: #1d6f52;
      --accent: #ecf7f1;
      --status-ok: #1f7a46;
      --status-bad: #b34747;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top right, #dfeedd 0%, transparent 28%),
        radial-gradient(circle at bottom left, #f4d6aa 0%, transparent 22%),
        linear-gradient(180deg, #f7f5ef 0%, #efeee8 100%);
    }
    .shell {
      max-width: 1280px;
      margin: 0 auto;
      padding: 24px;
    }
    .hero, .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      box-shadow: 0 18px 40px rgba(40, 32, 18, 0.08);
      backdrop-filter: blur(8px);
    }
    .hero {
      padding: 20px 22px;
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
      margin-bottom: 20px;
    }
    .hero h1 { margin: 0 0 6px; font-size: 1.8rem; }
    .hero p { margin: 0; color: var(--muted); }
    .toolbar {
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
    }
    .toolbar input {
      min-width: 260px;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px 12px;
      background: white;
    }
    .toolbar button {
      border: none;
      border-radius: 12px;
      padding: 10px 14px;
      cursor: pointer;
      background: linear-gradient(135deg, var(--brand), #2a9270);
      color: white;
      font-weight: 700;
    }
    .grid {
      display: grid;
      grid-template-columns: 380px 1fr;
      gap: 18px;
    }
    .list {
      padding: 14px;
      max-height: calc(100vh - 170px);
      overflow: auto;
    }
    .event {
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 12px;
      background: white;
      cursor: pointer;
      margin-bottom: 10px;
    }
    .event.active {
      border-color: var(--brand);
      background: var(--accent);
    }
    .row {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
    }
    .pill {
      border-radius: 999px;
      padding: 3px 9px;
      font-size: 0.78rem;
      font-weight: 700;
      background: #eef2ee;
    }
    .status-ok { color: var(--status-ok); }
    .status-bad { color: var(--status-bad); }
    .detail {
      padding: 18px;
      min-height: 70vh;
    }
    .meta {
      color: var(--muted);
      font-size: 0.92rem;
      margin-bottom: 14px;
    }
    .section {
      margin-bottom: 18px;
    }
    .section h3 {
      margin: 0 0 8px;
      font-size: 1rem;
    }
    pre {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      background: #fbfaf7;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px;
      max-height: 280px;
      overflow: auto;
      font-size: 0.86rem;
      line-height: 1.45;
    }
    @media (max-width: 980px) {
      .grid { grid-template-columns: 1fr; }
      .list { max-height: none; }
      .detail { min-height: auto; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <div class="hero">
      <div>
        <h1>Request Inspector</h1>
        <p>Live request and response capture for Twilio webhooks, chat calls, and API debugging.</p>
      </div>
      <div class="toolbar">
        <input id="filterInput" placeholder="Filter by path, method, body, or status" />
        <button id="refreshBtn" type="button">Refresh</button>
      </div>
    </div>
    <div class="grid">
      <div class="card list" id="eventList"></div>
      <div class="card detail" id="detailPane">
        <div class="meta">No requests captured yet.</div>
      </div>
    </div>
  </div>
  <script>
    let events = [];
    let activeId = null;

    function statusClass(status) {
      return status >= 400 ? 'status-bad' : 'status-ok';
    }

    function eventMatchesFilter(item, query) {
      if (!query) return true;
      const haystack = [
        item.method,
        item.path,
        item.query_string || '',
        String(item.response.status_code),
        item.request.body || '',
        item.response.body || ''
      ].join('\\n').toLowerCase();
      return haystack.includes(query.toLowerCase());
    }

    function renderList() {
      const list = document.getElementById('eventList');
      const query = document.getElementById('filterInput').value.trim();
      const visible = events.filter((item) => eventMatchesFilter(item, query));

      if (!visible.length) {
        list.innerHTML = '<div class="meta">No matching requests.</div>';
        renderDetail(null);
        return;
      }

      if (!activeId || !visible.some((item) => item.id === activeId)) {
        activeId = visible[0].id;
      }

      list.innerHTML = visible.map((item) => `
        <button class="event ${item.id === activeId ? 'active' : ''}" data-id="${item.id}">
          <div class="row">
            <strong>${item.method} ${item.path}</strong>
            <span class="pill ${statusClass(item.response.status_code)}">${item.response.status_code}</span>
          </div>
          <div class="meta">${new Date(item.created_at).toLocaleString()} • ${item.duration_ms} ms</div>
        </button>
      `).join('');

      list.querySelectorAll('.event').forEach((el) => {
        el.addEventListener('click', () => {
          activeId = el.dataset.id;
          renderList();
        });
      });

      renderDetail(visible.find((item) => item.id === activeId) || visible[0]);
    }

    function renderDetail(item) {
      const pane = document.getElementById('detailPane');
      if (!item) {
        pane.innerHTML = '<div class="meta">No requests captured yet.</div>';
        return;
      }

      pane.innerHTML = `
        <div class="meta">
          <strong>${item.method} ${item.path}</strong><br />
          ${new Date(item.created_at).toLocaleString()} • ${item.duration_ms} ms • status ${item.response.status_code}
        </div>
        <div class="section">
          <h3>Request Headers</h3>
          <pre>${escapeHtml(JSON.stringify(item.request.headers, null, 2))}</pre>
        </div>
        <div class="section">
          <h3>Request Body</h3>
          <pre>${escapeHtml(item.request.body || '(empty)')}</pre>
        </div>
        <div class="section">
          <h3>Response Headers</h3>
          <pre>${escapeHtml(JSON.stringify(item.response.headers, null, 2))}</pre>
        </div>
        <div class="section">
          <h3>Response Body</h3>
          <pre>${escapeHtml(item.response.body || '(empty)')}</pre>
        </div>
      `;
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;');
    }

    async function refresh() {
      const response = await fetch('/debug/inspector/events');
      events = await response.json();
      renderList();
    }

    document.getElementById('refreshBtn').addEventListener('click', refresh);
    document.getElementById('filterInput').addEventListener('input', renderList);
    refresh();
    setInterval(refresh, 2500);
  </script>
</body>
</html>"""
    return HTMLResponse(html)


@router.get("/inspector/events")
def inspector_events() -> list[dict[str, Any]]:
    return list(_events)
