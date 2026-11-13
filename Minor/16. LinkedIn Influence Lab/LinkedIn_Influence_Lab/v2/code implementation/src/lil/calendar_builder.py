"""Phase 3: merge slots + drafts into the 6-week calendar and write the Excel/CSV deliverable."""
from __future__ import annotations

import csv

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from .knowledge import FORMATS, PILLARS

HEADER_FILL = PatternFill("solid", fgColor="4C1D95")


def build_calendar(slots: list[dict], drafts: list[dict]) -> list[dict]:
    """Attach the draft whose slot_id matches each slot."""
    by_slot = {d["slot_id"]: d for d in drafts}
    rows = []
    for s in slots:
        d = by_slot.get(s["slot_id"], {})
        rows.append({**s, "pillar_label": PILLARS[s["pillar"]]["label"], "draft_id": d.get("id", ""),
                     "theme": d.get("hook", ""), "status": "Planned",
                     "quality": d.get("quality", ""), "human_reviewed": bool(d.get("human_reviewed"))})
    return rows


def _lighten(hex_color: str, amount: float = 0.78) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "".join(f"{int(c + (255 - c) * amount):02X}" for c in (r, g, b))


def write_excel(profile: dict, calendar: list[dict], drafts: list[dict], path) -> None:
    by_id = {d["id"]: d for d in drafts}
    wb = Workbook()
    ws = wb.active
    ws.title = "6-Week Calendar"
    thin = Side(style="thin", color="D9D6F0")
    cols = ["Week", "Date", "Day", "Time", "Pillar", "Format", "Pilot", "Theme (hook)", "Draft post", "Quality", "Reviewed", "Status"]
    ws.append([f"LinkedIn Content Calendar - {profile.get('name') or 'Author'} ({profile.get('persona', '').replace('_', ' ').title()})"])
    ws["A1"].font = Font(size=16, bold=True, color="FFFFFF")
    ws["A1"].fill = PatternFill("solid", fgColor="7C3AED")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(cols))
    ws.row_dimensions[1].height = 28
    ws.append(cols)
    for c in range(1, len(cols) + 1):
        cell = ws.cell(row=2, column=c)
        cell.font, cell.fill = Font(bold=True, color="FFFFFF"), HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
    for r in calendar:
        d = by_id.get(r["draft_id"], {})
        ws.append([r["week"], r["date"], r["weekday"], r["time"], r["pillar_label"], FORMATS[r["format"]]["label"],
                   "Yes" if r.get("is_pilot") else "", r["theme"], d.get("text", ""), r["quality"],
                   "Yes" if r["human_reviewed"] else "No", r["status"]])
        fill = PatternFill("solid", fgColor=_lighten(PILLARS[r["pillar"]]["color"]))
        for c in range(1, len(cols) + 1):
            cell = ws.cell(row=ws.max_row, column=c)
            cell.fill, cell.border = fill, Border(top=thin, bottom=thin, left=thin, right=thin)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    for i, w in enumerate([6, 12, 11, 8, 20, 14, 7, 42, 70, 9, 10, 11], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A3"
    last = max(3, ws.max_row)
    dv = DataValidation(type="list", formula1='"Planned,Published,Skipped,Rescheduled"', allow_blank=False)
    ws.add_data_validation(dv)
    dv.add(f"L3:L{last}")

    # week grid
    wg = wb.create_sheet("Week View")
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    wg.append(["Week"] + days)
    for c in range(1, 9):
        wg.cell(row=1, column=c).font, wg.cell(row=1, column=c).fill = Font(bold=True, color="FFFFFF"), HEADER_FILL
    for w in sorted({r["week"] for r in calendar}):
        row = [f"Week {w}"] + [""] * 7
        wg.append(row)
        for r in (x for x in calendar if x["week"] == w):
            col = 2 + days.index(r["weekday"])
            cell = wg.cell(row=wg.max_row, column=col, value=f"{r['pillar_label']}\n{FORMATS[r['format']]['emoji']} {FORMATS[r['format']]['label']}")
            cell.fill = PatternFill("solid", fgColor=_lighten(PILLARS[r["pillar"]]["color"], 0.55))
            cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        wg.row_dimensions[wg.max_row].height = 44
    wg.column_dimensions["A"].width = 9
    for c in range(2, 9):
        wg.column_dimensions[get_column_letter(c)].width = 19

    lg = wb.create_sheet("Legend")
    lg.append(["Pillar", "What it covers"])
    for k, p in PILLARS.items():
        lg.append([p["label"], p["desc"]])
        lg.cell(row=lg.max_row, column=1).fill = PatternFill("solid", fgColor=_lighten(p["color"], 0.45))
    lg.column_dimensions["A"].width = 22
    lg.column_dimensions["B"].width = 70
    wb.save(path)


def write_csv(calendar: list[dict], drafts: list[dict], path) -> None:
    by_id = {d["id"]: d for d in drafts}
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["week", "date", "weekday", "time", "pillar", "format", "pilot", "theme", "draft", "quality", "reviewed", "status"])
        for r in calendar:
            w.writerow([r["week"], r["date"], r["weekday"], r["time"], r["pillar_label"], r["format"],
                        "yes" if r["is_pilot"] else "", r["theme"], by_id.get(r["draft_id"], {}).get("text", ""),
                        r["quality"], "yes" if r["human_reviewed"] else "no", r["status"]])
