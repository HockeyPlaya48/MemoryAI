"""MemoryAI — Streamlit Demo Interface."""

import json
import requests
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="MemoryAI", page_icon="🧠", layout="centered")

st.markdown("""
<style>
    .stApp { background-color: #0d1117; }
    h1 { color: #58a6ff; }
    .source-card {
        background: #161b22; border: 1px solid #30363d;
        border-radius: 8px; padding: 1rem; margin: 0.5rem 0;
    }
    .source-score { color: #3fb950; font-weight: 700; }
    .connection-tag {
        display: inline-block; background: #1f2937; border: 1px solid #374151;
        border-radius: 16px; padding: 2px 10px; margin: 2px; font-size: 0.85rem; color: #9ca3af;
    }
</style>
""", unsafe_allow_html=True)

st.title("🧠 MemoryAI")
st.caption("AI-native knowledge base — ingest data, query with context, navigate with agents")

# Check API health
try:
    health = requests.get(f"{API_BASE}/health", timeout=3).json()
    st.success(f"API connected — {health.get('status', 'unknown')}")
except Exception:
    st.error("API not running. Start it with: `uvicorn app.main:app --reload`")
    st.stop()

# Tabs
tab_ingest, tab_query, tab_navigate, tab_admin = st.tabs(["📥 Ingest", "🔍 Query", "🧭 Navigate", "⚙️ Admin"])

# ─── Ingest Tab ──────────────────────────────────────────────────────────────────
with tab_ingest:
    st.subheader("Add data to your knowledge base")

    ingest_type = st.radio("Data type", ["Text", "File Upload", "Web URL"], horizontal=True)

    if ingest_type == "Text":
        text_input = st.text_area("Paste your text", height=200, placeholder="Paste any text, notes, articles...")
        source_name = st.text_input("Source name (optional)", placeholder="e.g., meeting_notes_feb2026")
        if st.button("Ingest Text", type="primary"):
            if text_input.strip():
                with st.spinner("Processing..."):
                    resp = requests.post(f"{API_BASE}/ingest/text", json={
                        "text": text_input, "source": source_name or "direct_input"
                    })
                if resp.status_code == 200:
                    data = resp.json()
                    st.success(f"Ingested! Doc ID: `{data['doc_id']}` — {data['chunks_created']} chunks created")
                else:
                    st.error(f"Error: {resp.json().get('detail', 'Unknown error')}")

    elif ingest_type == "File Upload":
        uploaded = st.file_uploader("Upload PDF, TXT, or MD", type=["pdf", "txt", "md"])
        if uploaded and st.button("Ingest File", type="primary"):
            with st.spinner("Processing..."):
                resp = requests.post(f"{API_BASE}/ingest/file", files={"file": (uploaded.name, uploaded.getvalue())})
            if resp.status_code == 200:
                data = resp.json()
                st.success(f"Ingested! Doc ID: `{data['doc_id']}` — {data['chunks_created']} chunks created")
            else:
                st.error(f"Error: {resp.json().get('detail', 'Unknown error')}")

    elif ingest_type == "Web URL":
        url_input = st.text_input("Enter URL", placeholder="https://example.com/article")
        if st.button("Ingest URL", type="primary"):
            if url_input.strip():
                with st.spinner("Fetching and processing..."):
                    resp = requests.post(f"{API_BASE}/ingest/url", json={"url": url_input})
                if resp.status_code == 200:
                    data = resp.json()
                    st.success(f"Ingested! Doc ID: `{data['doc_id']}` — {data['chunks_created']} chunks created")
                else:
                    st.error(f"Error: {resp.json().get('detail', 'Unknown error')}")

# ─── Query Tab ───────────────────────────────────────────────────────────────────
with tab_query:
    st.subheader("Ask your knowledge base anything")

    question = st.text_input("Your question", placeholder="e.g., Summarize the key trends from my uploaded documents")
    n_results = st.slider("Max sources to retrieve", 3, 20, 10)

    if st.button("Search", type="primary", key="query_btn"):
        if question.strip():
            with st.spinner("Searching..."):
                resp = requests.post(f"{API_BASE}/query", json={"question": question, "n_results": n_results})
            if resp.status_code == 200:
                data = resp.json()

                # Answer
                st.markdown("### Answer")
                st.markdown(data.get("answer", "No answer generated"))

                # Sources
                sources = data.get("sources", [])
                if sources:
                    st.markdown(f"### Sources ({len(sources)})")
                    for i, src in enumerate(sources):
                        with st.expander(f"Source {i+1}: {src['source']} (relevance: {src['relevance_score']:.2f})"):
                            st.markdown(src["text"])

                # Connections
                connections = data.get("connections", [])
                if connections:
                    st.markdown("### Entity Connections")
                    for conn in connections:
                        related = ", ".join(conn["related"])
                        st.markdown(f"**{conn['entity']}** ({conn['type']}) → {related}")

                # Raw JSON
                with st.expander("Raw JSON response"):
                    st.json(data)
            else:
                st.error(f"Error: {resp.json().get('detail', 'Unknown error')}")

# ─── Navigate Tab ────────────────────────────────────────────────────────────────
with tab_navigate:
    st.subheader("Agent Navigation — threaded context")
    st.caption("Maintain conversation context across queries. Agents can run parallel sessions.")

    if "nav_session_id" not in st.session_state:
        st.session_state.nav_session_id = ""
    if "nav_history" not in st.session_state:
        st.session_state.nav_history = []

    col1, col2 = st.columns([3, 1])
    with col1:
        session_id = st.text_input("Session ID (leave blank to create new)", value=st.session_state.nav_session_id)
    with col2:
        if st.button("New Session"):
            st.session_state.nav_session_id = ""
            st.session_state.nav_history = []
            st.rerun()

    nav_question = st.text_input("Your question", placeholder="Ask something...", key="nav_q")

    if st.button("Navigate", type="primary", key="nav_btn"):
        if nav_question.strip():
            with st.spinner("Navigating..."):
                payload = {"question": nav_question, "n_results": 10}
                if session_id.strip():
                    payload["session_id"] = session_id.strip()
                resp = requests.post(f"{API_BASE}/navigate", json=payload)

            if resp.status_code == 200:
                data = resp.json()
                st.session_state.nav_session_id = data.get("session_id", "")
                st.session_state.nav_history.append({
                    "question": nav_question,
                    "answer": data.get("answer", ""),
                    "turn": data.get("session_turns", 0),
                })

                st.info(f"Session: `{data.get('session_id')}` — Turn {data.get('session_turns', 0)}")
                st.markdown("### Answer")
                st.markdown(data.get("answer", ""))

                sources = data.get("sources", [])
                if sources:
                    with st.expander(f"Sources ({len(sources)})"):
                        for src in sources:
                            st.markdown(f"- **{src['source']}** ({src['relevance_score']:.2f}): {src['text'][:200]}...")
            else:
                st.error(f"Error: {resp.json().get('detail', 'Unknown error')}")

    # Show session history
    if st.session_state.nav_history:
        st.markdown("### Session History")
        for turn in reversed(st.session_state.nav_history):
            with st.expander(f"Turn {turn['turn']}: {turn['question'][:60]}..."):
                st.markdown(turn["answer"])

# ─── Admin Tab ───────────────────────────────────────────────────────────────────
with tab_admin:
    st.subheader("Knowledge Base Stats")

    if st.button("Refresh Stats"):
        pass  # Just triggers re-render

    try:
        resp = requests.get(f"{API_BASE}/collections", timeout=5)
        if resp.status_code == 200:
            stats = resp.json()
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Documents", stats.get("total_documents", 0))
            col2.metric("Chunks", stats.get("total_chunks", 0))
            col3.metric("Entities", stats.get("unique_entities", 0))
            col4.metric("Relations", stats.get("total_relations", 0))

            sources = stats.get("sources", [])
            if sources:
                st.markdown("### Indexed Sources")
                for src in sources:
                    st.markdown(f"- `{src}`")
    except Exception:
        st.warning("Could not fetch stats")

    st.markdown("---")
    st.subheader("Delete Document")
    del_doc_id = st.text_input("Document ID to delete", placeholder="e.g., a1b2c3d4e5f6g7h8")
    if st.button("Delete", type="secondary"):
        if del_doc_id.strip():
            resp = requests.delete(f"{API_BASE}/documents/{del_doc_id.strip()}")
            if resp.status_code == 200:
                data = resp.json()
                st.success(f"Deleted {data.get('chunks_deleted', 0)} chunks for doc `{del_doc_id}`")
            else:
                st.error("Delete failed")
