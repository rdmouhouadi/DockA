import streamlit as st
import requests

API_BASE_URL = "http://api:8000"

st.set_page_config(
    page_title="DocKA",
    page_icon="📘",
    layout="wide"
)

st.title("📘 DocKA — Document Knowledge Access")
st.caption("Search your knowledge base using keyword search (BM25)")

# ---------------------------------------------------------------------------
# Search bar
# ---------------------------------------------------------------------------
col1, col2 = st.columns([5, 1])

with col1:
    query = st.text_input(
        label="Search query",
        placeholder="e.g. bluetooth alarme compteur...",
        label_visibility="collapsed"
    )

with col2:
    size = st.selectbox("Results", [5, 10, 20], index=1, label_visibility="collapsed")

search_clicked = st.button("🔍 Search", use_container_width=False)

# ---------------------------------------------------------------------------
# Search execution
# ---------------------------------------------------------------------------
if search_clicked and query.strip():
    try:
        response = requests.get(
            f"{API_BASE_URL}/search",
            params={"q": query, "size": size},
            timeout=5
        )
        data = response.json()

        if response.status_code != 200:
            st.error(f"Search failed: {data.get('detail', 'Unknown error')}")
        else:
            total = data["total"]
            results = data["results"]

            st.markdown(f"**{total} documents found** for `{query}`")
            st.divider()

            if not results:
                st.info("No results found. Try a different query.")
            else:
                for r in results:
                    with st.container():
                        col_title, col_score = st.columns([6, 1])

                        with col_title:
                            st.markdown(f"### 📄 {r['title']}")

                        with col_score:
                            st.metric(label="Score", value=round(r["score"], 2))

                        st.caption(f"📁 {r['path']}  |  🏷️ Source: `{r['source']}`")

                        # Render snippet with HTML highlights
                        snippet = r.get("snippet", "")
                        if snippet:
                            # Replace newlines for cleaner display
                            snippet_html = snippet.replace("\n", " ")
                            st.markdown(
                                f"<div style='background:#f0f2f6;padding:10px;"
                                f"border-radius:6px;font-size:0.9em'>{snippet_html}</div>",
                                unsafe_allow_html=True
                            )

                        st.divider()

    except Exception as e:
        st.error(f"Could not reach API: {e}")

elif search_clicked and not query.strip():
    st.warning("Please enter a search query.")

# ---------------------------------------------------------------------------
# Sidebar — API health
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ System Status")
    if st.button("Check health"):
        try:
            r = requests.get(f"{API_BASE_URL}/health", timeout=3)
            health = r.json()
            st.success("API reachable")
            for service, status in health.items():
                icon = "✅" if status == "ok" else "❌"
                st.write(f"{icon} {service}: {status}")
        except Exception as e:
            st.error(f"API unreachable: {e}")