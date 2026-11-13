import csv

PLUGIN = {
    "id": "export_taplio", "name": "Taplio Queue (CSV + copy-paste pack)", "category": "export", "icon": "🗓️",
    "default_enabled": True,
    "description": "Creates Taplio-ready posting queues. Taplio's plans and import options change, so this "
                   "gives you clean per-post text and a schedule you can paste into Taplio's composer.",
    "fields": [],
}

COLS = ["Scheduled Date", "Scheduled Time", "Timezone", "Post Text", "Format", "Pillar",
        "Human Reviewed", "Notes"]


def _notes(d):
    if d["format"] == "poll" and d.get("poll"):
        p = d["poll"]
        return "Create as native poll. Q: " + p["question"] + " | Options: " + " / ".join(p["options"])
    if d["format"] == "carousel" and d.get("slides"):
        return "Build as PDF carousel: " + " > ".join(s["title"] for s in d["slides"])
    return ""


def export(profile, calendar, drafts, out_dir):
    by_id = {d["id"]: d for d in drafts}
    rows = []
    for slot in calendar:
        d = by_id.get(slot.get("draft_id"))
        if not d:
            continue
        rows.append([slot["date"], slot["time"], profile.get("timezone", ""), d["text"], d["format"],
                     slot["pillar"], "Y" if d.get("human_reviewed") else "N", _notes(d)])
    files = []
    for name, subset in (("taplio_queue_all_needs_review.csv", rows),
                         ("taplio_queue_approved_only.csv", [r for r in rows if r[6] == "Y"])):
        path = out_dir / name
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow(COLS)
            w.writerows(subset)
        files.append(path)
    pack = out_dir / "copy_paste_pack.txt"
    with open(pack, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(f"=== {r[0]} {r[1]} ({r[5]} | {r[4]}) | reviewed: {r[6]} ===\n{r[3]}\n")
            if r[7]:
                fh.write(f"[{r[7]}]\n")
            fh.write("\n")
    files.append(pack)
    return files
