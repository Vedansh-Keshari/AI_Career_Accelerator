PLUGIN = {
    "id": "ai_offline", "name": "Built-in Template Engine (no key needed)", "category": "ai", "icon": "🧩",
    "default_enabled": True,
    "description": "Works with no internet and no API key. Builds ideas and drafts from your inputs and the "
                   "idea bank. Best for a first pass; connect an AI plugin for richer writing.",
    "fields": [],
}


def complete(cfg, system, prompt):
    raise NotImplementedError("The offline engine is handled inside ideation/drafting.")
