import streamlit as st
import requests

st.set_page_config(page_title="DocKA", layout="wide")

st.title("📘 DocKA – Support Knowledge Platform")

st.write("This is the DocKA UI. Backend connectivity test below.")

if st.button("Check API health"):
    try:
        r = requests.get("http://api:8000/health", timeout=3)
        st.success("API reachable")
        st.json(r.json())
    except Exception as e:
        st.error(f"API unreachable: {e}")

