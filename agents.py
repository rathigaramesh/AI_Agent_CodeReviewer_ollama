# agents.py
import os
import json
import time
import logging
import socket
from typing import Dict

# Setup logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/ollama_agents.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

try:
    import ollama
    _HAS_OLLAMA = True
except Exception:
    _HAS_OLLAMA = False
    import requests

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:latest")
OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://localhost:11434")


def _is_ollama_running() -> bool:
    """Check if Ollama is running on localhost:11434."""
    try:
        sock = socket.create_connection(("localhost", 11434), timeout=2)
        sock.close()
        return True
    except Exception:
        return False


def _call_model(prompt: str) -> str:
    """Call Ollama using Python package if available, else REST /api/chat."""
    if not _is_ollama_running():
        err_msg = "Ollama server is not running. Please start it before proceeding."
        logging.error(err_msg)
        return err_msg

    logging.info(f"Prompt sent to model {OLLAMA_MODEL}: {prompt[:200]}...")

    # Preferred: Python package
    if _HAS_OLLAMA:
        try:
            resp = ollama.chat(
                model=OLLAMA_MODEL,
                messages=[{"role": "system", "content": "You are a helpful assistant."},
                          {"role": "user", "content": prompt}]
            )
            result = resp["message"]["content"]
            logging.info(f"Response from model: {result[:200]}...")
            return result
        except Exception as e:
            logging.error(f"ollama.chat() failed: {e}")

    # REST API fallback
    try:
        import requests
        payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
        url = f"{OLLAMA_BASE}/api/chat"
        headers = {"Content-Type": "application/json"}
        r = requests.post(url, json=payload, headers=headers, timeout=120)
        r.raise_for_status()
        data = r.json()

        if "message" in data:
            result = data["message"]["content"]
        elif "messages" in data:
            result = "\n".join(m.get("content", "") for m in data["messages"])
        else:
            result = str(data)

        logging.info(f"Response from REST API: {result[:200]}...")
        return result
    except Exception as e:
        err_msg = f"ERROR calling Ollama chat API: {e}"
        logging.error(err_msg)
        return err_msg


# ===== Agents =====

def review_code_agent(filename: str, content: str) -> Dict:
    prompt = f"""You are a senior software engineer. Perform a code review on {filename}.

1) High level summary of intent.
2) Bugs or syntax errors with line hints.
3) Suggested fixes.
4) Tests to add.
5) Risk areas.

File Content:
{content[:15000]}
"""
    return {"agent": "code_review", "result": _call_model(prompt)}


def vulnerability_agent(filename: str, content: str) -> Dict:
    prompt = f"""You are a security engineer. Analyze {filename} for vulnerabilities:
- XSS
- SQL injection
- Insecure deserialization
- File handling issues
- Secrets in code
- Misconfigurations

Give severity and fixes.

Content:
{content[:15000]}
"""
    return {"agent": "vulnerability", "result": _call_model(prompt)}


def efficiency_agent(filename: str, content: str) -> Dict:
    prompt = f"""You are a performance engineer. Review {filename} for:
- Algorithm inefficiencies
- Memory/CPU issues
- Inefficient I/O

Give suggestions and code examples.

Content:
{content[:15000]}
"""
    return {"agent": "efficiency", "result": _call_model(prompt)}


def impact_agent(filename: str, content: str) -> Dict:
    prompt = f"""You are a release manager. Based on {filename} changes, give:
- Impact on services/modules/configs
- DB migration needs
- Backward compatibility
- Rollout strategy
- Tests and monitoring

Content:
{content[:15000]}
"""
    return {"agent": "impact", "result": _call_model(prompt)}


def approval_agent(head_identifier: str, filename: str, review: Dict, vuln: Dict, eff: Dict, impact: Dict) -> Dict:
    prompt = f"""You are the Head of Engineering.

Summarize:
--- CODE REVIEW ---
{review.get('result')}

--- VULNERABILITY ---
{vuln.get('result')}

--- EFFICIENCY ---
{eff.get('result')}

--- IMPACT ---
{impact.get('result')}

Give a verdict: approve or reject, and list any constraints.
"""
    resp = _call_model(prompt)
    verdict = "rejected"
    if "approve" in resp.lower() and "reject" not in resp.lower():
        verdict = "approved"
    return {"agent": "approval", "result": resp, "status": verdict}


def deploy_agent(filename: str, content: str, approval: Dict) -> Dict:
    os.makedirs("deployed", exist_ok=True)
    out_path = os.path.join("deployed", filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)

    steps = [
        "Checkout commit / create branch",
        "Run tests",
        "Run DB migrations",
        "Canary deploy to staging",
        "Monitor logs and metrics",
        "Promote to production"
    ]
    logging.info(f"Deployed file saved to {out_path}")
    return {"agent": "deploy", "deployed_path": out_path, "steps": steps, "approval": approval}
