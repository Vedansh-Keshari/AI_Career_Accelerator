import csv

PLUGIN = {
    "id": "export_sheets", "name": "Google Sheets / Drive pack", "category": "export", "icon": "📗",
    "default_enabled": True,
    "description": "Writes a Sheets-friendly calendar CSV and an engagement tracking template. Upload to "
                   "Google Drive (File > Import in Sheets) and share with the email you set.",
    "fields": [{"key": "share_note", "label": "Reminder note (optional)", "type": "text", "default": "",
                "help": "Text, up to 160 characters. Printed next to the files."}],
}


def export(profile, calendar, drafts, out_dir):
    by_id = {d["id"]: d for d in drafts}
    path = out_dir / "calendar_for_google_sheets.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["Date", "Weekday", "Time", "Week", "Pillar", "Format", "Pilot", "Theme", "Draft", "Status"])
        for s in calendar:
            d = by_id.get(s.get("draft_id"), {})
            w.writerow([s["date"], s["weekday"], s["time"], s["week"], s["pillar_label"], s["format"],
                        "Yes" if s.get("is_pilot") else "", s.get("theme", ""), d.get("text", ""), s.get("status", "Planned")])
    note = out_dir / "UPLOAD_TO_DRIVE.txt"
    note.write_text(
        "1. Open Google Drive > New > File upload, choose calendar_for_google_sheets.csv\n"
        "2. Right-click > Open with > Google Sheets\n"
        f"3. Share with: {profile.get('google_email') or '(add your Google email in Inputs)'}\n", encoding="utf-8")
    return [path, note]
