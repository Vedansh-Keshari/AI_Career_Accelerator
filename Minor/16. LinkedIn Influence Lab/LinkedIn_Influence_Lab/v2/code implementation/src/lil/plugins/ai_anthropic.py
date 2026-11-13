import os

import requests

PLUGIN = {
    "id": "ai_anthropic", "name": "Claude (Anthropic API)", "category": "ai", "icon": "✨",
    "description": "Uses the Anthropic Messages API for ideas, drafts and rewrites. Needs your own API key "
                   "(or the ANTHROPIC_API_KEY environment variable).",
    "fields": [
        {"key": "api_key", "label": "Anthropic API key", "type": "password", "default": "",
         "help": "Text starting with sk-ant-. Stored only in data/inputs/plugins.json on your machine."},
        {"key": "model", "label": "Model name", "type": "text", "default": "claude-sonnet-5-5",
         "help": "Text. Change this if you prefer another Claude model."},
    ],
}


def complete(cfg, system, prompt):
    key = cfg.get("api_key") or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("No Anthropic API key set (Plugins page or ANTHROPIC_API_KEY).")
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": cfg.get("model") or "claude-sonnet-5-5", "max_tokens": 2000, "system": system,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=90,
    )
    resp.raise_for_status()
    blocks = resp.json().get("content", [])
    return "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
