# app.py
import streamlit as st
from agents import (
    review_code_agent,
    vulnerability_agent,
    efficiency_agent,
    impact_agent,
    approval_agent,
    deploy_agent,
    _is_ollama_running,
)
import os
from datetime import datetime

# ---- PAGE SETTINGS ----
st.set_page_config(page_title="Ollama Multi-Agent Code Review", layout="wide", page_icon="🛠️")

# ---- CUSTOM CSS ----
st.markdown("""
    <style>
    body {
        background-color: #f7f9fc;
        font-family: 'Segoe UI', sans-serif;
    }
    .main-title {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f4e79;
        text-align: center;
        padding: 10px 0;
    }
    .section-title {
        font-size: 1.3rem;
        font-weight: bold;
        color: #0f4c75;
        margin-top: 20px;
        margin-bottom: 5px;
    }
    .card {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .approval-approved {
        background-color: #d4edda;
        color: #155724;
        padding: 10px;
        border-radius: 5px;
    }
    .approval-rejected {
        background-color: #f8d7da;
        color: #721c24;
        padding: 10px;
        border-radius: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# ---- HEADER ----
st.markdown('<div class="main-title">🤖 Ollama Multi-Agent Code Review & Deployment</div>', unsafe_allow_html=True)
st.write("Upload `.java`, `.js`, or `.properties` files. Agents will review, analyze vulnerabilities, suggest efficiency improvements, assess impact, request approval, and deploy if approved.")

# ---- OLLAMA CHECK ----
if not _is_ollama_running():
    st.error("🚫 Ollama server is not running. Please start it before proceeding.")
    st.stop()
else:
    st.success("✅ Ollama server is running and ready.")

# ---- FILE UPLOAD ----
uploaded = st.file_uploader("📂 Upload Code File", type=["java", "js", "properties"])

if uploaded:
    content = uploaded.read().decode(errors='ignore')
    filename = uploaded.name

    st.markdown(f"**📄 File Name:** `{filename}`")
    st.code(content[:500], language='text')

    st.info("⚙️ Running agents... Please wait...")

    # ---- AGENT CALLS ----
    review = review_code_agent(filename, content)
    vuln = vulnerability_agent(filename, content)
    eff = efficiency_agent(filename, content)
    impact = impact_agent(filename, content)

    # ---- DISPLAY RESULTS ----
    st.markdown('<div class="section-title">📝 Code Review</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="card">{review["result"]}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">🔒 Vulnerability Scan</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="card">{vuln["result"]}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">⚡ Efficiency Suggestions</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="card">{eff["result"]}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">📊 Impact Analysis</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="card">{impact["result"]}</div>', unsafe_allow_html=True)

    # ---- APPROVAL ----
    st.markdown('<div class="section-title">✅ Approval Workflow</div>', unsafe_allow_html=True)
    head_email = st.text_input("Approver (Name or Email)", value="head@example.com")
    if st.button("📨 Request Approval"):
        approval = approval_agent(head_email, filename, review, vuln, eff, impact)
        if approval["status"] == "approved":
            st.markdown(f'<div class="approval-approved">{approval["result"]}</div>', unsafe_allow_html=True)
            if st.button("🚀 Deploy to Server"):
                deploy_result = deploy_agent(filename, content, approval)
                st.success(f"Deployed to `{deploy_result['deployed_path']}`")
                st.json(deploy_result)
        else:
            st.markdown(f'<div class="approval-rejected">{approval["result"]}</div>', unsafe_allow_html=True)

    # ---- AUDIT ----
    if st.button("💾 Save Audit Log"):
        os.makedirs("audit", exist_ok=True)
        audit_path = os.path.join("audit", f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(audit_path, "w", encoding="utf-8") as f:
            import json
            json.dump({
                "filename": filename,
                "review": review,
                "vulnerability": vuln,
                "efficiency": eff,
                "impact": impact
            }, f, indent=2)
        st.success(f"Audit log saved to `{audit_path}`")
