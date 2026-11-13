import os

import requests

PLUGIN = {
    "id": "ai_openai", "name": "ChatGPT (OpenAI API)", "category": "ai", "icon": "🤖",
    "description": "Uses the OpenAI chat API for ideas, drafts and rewrites. Needs your own API key "
                   "(or the OPENAI_API_KEY environment variable). Billed by OpenAI, not by this project.",
    "fields": [
        {"key": "api_key", "label": "OpenAI API key", "type": "password", "default": "",
         "help": "Starts with sk-. Stored only in data/inputs/plugins.json on your machine."},
        {"key": "model", "label": "Model name", "type": "text", "default": "gpt-4o-mini",
         "help": "Any chat model your account can use."},
        {"key": "temperature", "label": "Creativity (0-1)", "type": "text", "default": "0.8", "help": ""},
    ],
}


def complete(cfg, system, prompt):
    key = cfg.get("api_key") or os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("No OpenAI API key set (Plugins page or OPENAI_API_KEY).")
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": cfg.get("model") or "gpt-4o-mini",
              "temperature": float(cfg.get("temperature") or 0.8),
              "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]},
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()
