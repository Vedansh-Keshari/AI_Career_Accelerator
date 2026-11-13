from datetime import datetime, timedelta, timezone

PLUGIN = {
    "id": "export_ical", "name": "Calendar reminders (.ics)", "category": "export", "icon": "⏰",
    "default_enabled": True,
    "description": "Creates an .ics file with a reminder for every post. Import into Google, Outlook or "
                   "Apple Calendar so you never miss a posting slot.",
    "fields": [{"key": "minutes", "label": "Reminder length (minutes)", "type": "text", "default": "30", "help": ""}],
}


def _esc(t):
    return str(t).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def export(profile, calendar, drafts, out_dir, minutes=30):
    tz = profile.get("timezone", "UTC")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//LinkedIn Influence Lab//EN", "CALSCALE:GREGORIAN"]
    for s in calendar:
        start = datetime.fromisoformat(f"{s['date']}T{s['time']}:00")
        end = start + timedelta(minutes=minutes)
        lines += ["BEGIN:VEVENT", f"UID:{s['slot_id']}-{s['date']}@linkedin-influence-lab",
                  f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
                  f"DTSTART;TZID={tz}:{start.strftime('%Y%m%dT%H%M%S')}",
                  f"DTEND;TZID={tz}:{end.strftime('%Y%m%dT%H%M%S')}",
                  f"SUMMARY:{_esc('LinkedIn post: ' + s.get('theme', s['pillar_label']))}",
                  f"DESCRIPTION:{_esc(s['pillar_label'] + ' | ' + s['format'])}", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    path = out_dir / "linkedin_posting_reminders.ics"
    path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    return [path]
