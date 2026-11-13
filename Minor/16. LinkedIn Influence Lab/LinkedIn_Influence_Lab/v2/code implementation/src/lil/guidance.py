"""What to type, in which format, and why. One source for tooltips, the data guide table and validation."""
from __future__ import annotations

import re
from datetime import date

from .knowledge import PILLARS, TIMEZONES, WEEKDAYS

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LINKEDIN = re.compile(r"^https?://([a-z]{2,3}\.)?linkedin\.com/in/[A-Za-z0-9\-_%]+/?$", re.I)

# key, label, datatype, rule, example, why we ask, required?
FIELD_GUIDE = [
    ("persona", "Path", "Choice (3 options)", "Professional, Job Seeker or Thought Leader.", "Job Seeker", "Changes tabs, pillar mix, rhythm, call-to-action wording and KPIs.", True),
    ("name", "Full name", "Text, 2-80 characters", "Letters, spaces, dots, hyphens, apostrophes.", "Riya Mehta", "Used in drafts, reports and file titles.", True),
    ("email", "Email ID", "Email address", "name@domain.com", "riya@example.com", "Printed on reports. Never used to log in anywhere.", False),
    ("linkedin_url", "LinkedIn profile URL", "Web address", "https://www.linkedin.com/in/your-name", "https://www.linkedin.com/in/riya-mehta", "Printed on the audit; helps you check the right profile.", False),
    ("taplio_account", "Taplio account", "Text, 3-80 characters", "The email or username you use for Taplio. Never a password.", "riya@example.com", "Reminds you which account the queue is for.", False),
    ("google_email", "Google account", "Email address", "Gmail or Workspace address.", "riya@gmail.com", "Used in the Drive/Sheets upload note.", False),
    ("current_role", "Current role", "Text, 2-80 characters", "Your job title today.", "Senior Operations Analyst", "Fills hooks such as '3 skills that separate good {role}s from great ones'.", True),
    ("company", "Company", "Text, up to 80 characters", "Leave blank if between roles.", "Northwind Logistics", "Used in headline options.", False),
    ("industry", "Industry / niche", "Text, 2-80 characters", "Lower-case phrase that fits 'work in ___'.", "supply chain analytics", "Fills hooks and hashtags.", True),
    ("years_experience", "Years of experience", "Whole number 0-60 (or blank)", "Digits only.", "6", "Used in hooks like '6 years in analytics taught me...'.", False),
    ("skills", "Key skills", "List, 2-20 items", "Comma separated, most important first, each up to 40 characters.", "Excel, SQL, Power BI", "First three skills feed headlines and tips; the first becomes a hashtag.", True),
    ("target_audience", "Target audience", "Text, 3-100 characters", "Who should read your posts.", "operations and supply chain professionals", "Fills hooks and calls to action.", True),
    ("goal", "Main goal", "Text, 5-160 characters", "One measurable-sounding sentence.", "Land interviews for BI analyst roles", "Shown in reports and passed to the AI.", True),
    ("target_roles", "Target roles", "Text, up to 100 characters", "Job seekers: the role(s) you want.", "Business Intelligence Analyst", "Headline ends with 'Open to ...'; recruiter hub keyword matching.", False),
    ("offer", "What you offer", "Text, up to 120 characters", "Thought leaders: your service or product.", "AI adoption workshops", "Fills authority hooks and headline.", False),
    ("tone", "Brand voice", "Choice (5 options)", "Pick the closest.", "Professional but relatable", "Adjusts calls to action and rewrites.", True),
    ("pillars", "Content pillars", "Choose 3-5", "From the five pillars in the brief.", "Career Insights, Actionable Tips, Personal Journey", "Sets what you post about and the mix.", True),
    ("story_win", "A recent win", "Text, up to 400 characters", "One true sentence with a result if possible.", "Cut weekly report time from 5 hours to 40 minutes.", "Becomes real examples in drafts. Blank = [placeholder].", False),
    ("story_mistake", "A mistake you learned from", "Text, up to 400 characters", "One honest sentence.", "I sent figures without checking duplicates.", "Authentic micro-stories.", False),
    ("story_lesson", "A lesson", "Text, up to 400 characters", "What you would tell your younger self.", "Check data for 10 minutes before every review.", "Closing lines and tips.", False),
    ("achievements", "Achievements with numbers", "Lines, up to 8 (160 characters each)", "One per line, start with a verb, include a number.", "Trained 12 teammates on pivot tables", "Proof lines in posts and your About draft.", False),
    ("current_headline", "Current LinkedIn headline", "Text, up to 220 characters", "Copy it from LinkedIn.", "Senior Operations Analyst at Northwind", "Scored in the audit and shown next to the optimized options.", False),
    ("current_about", "Current About section", "Text, up to 2,600 characters", "Copy it from LinkedIn.", "I help teams...", "Scored on length and a call to action.", False),
    ("followers", "Followers", "Whole number >= 0", "As shown on your profile.", "640", "Baseline for growth.", False),
    ("connections", "Connections", "Whole number >= 0", "As shown on your profile (500+ is shown as 500+; type 500).", "710", "Network-size check (500+).", False),
    ("posts_per_month_now", "Posts per month right now", "Whole number >= 0", "Posts you actually publish today.", "2", "Cadence check (8+ a month).", False),
    ("role_models", "Role models / competitors", "Lines: Name | URL | what you admire", "One per line, URL optional.", "Sample Peer | https://www.linkedin.com/in/sample | weekly carousels", "Benchmark table and peer-engagement list.", False),
    ("days", "Posting days", "Choose 2-5 weekdays", "Days you can reliably post.", "Tuesday, Wednesday, Thursday", "Sets the 6-week calendar.", True),
    ("time", "Posting time", "Time HH:MM (24h)", "Your local time.", "08:30", "Printed in calendar and reminders.", True),
    ("timezone", "Time zone", "Choice", "Pick the zone for your audience.", "Asia/Kolkata", "Used in the .ics reminders.", True),
    ("start_date", "First posting date", "Date YYYY-MM-DD", "A day on or after today.", "2026-11-16", "Anchors the 6 weeks.", True),
]

LOG_GUIDE = [
    ("Published on", "Date", "The day the post went live.", "2026-11-18"),
    ("Impressions", "Whole number >= 0", "LinkedIn: open the post > View analytics > Impressions.", "1140"),
    ("Likes / reactions", "Whole number >= 0", "All reaction types added together.", "52"),
    ("Comments", "Whole number >= 0", "Count of comments, not replies you wrote.", "9"),
    ("Shares / reposts", "Whole number >= 0", "Reposts with and without a comment.", "3"),
    ("Profile visits", "Whole number >= 0", "Profile viewers that came from the post (or the week's total if that is all you have).", "26"),
]
IMPORT_GUIDE = [
    ("post_id (optional)", "Text", "Draft id such as D03. If absent, rows are matched to your posts in calendar order."),
    ("Date / published_date (optional)", "YYYY-MM-DD", "When the post went live."),
    ("Impressions", "Whole number", "Also accepted: Views, Post impressions."),
    ("Reactions or Likes", "Whole number", ""),
    ("Comments", "Whole number", ""),
    ("Reposts or Shares", "Whole number", ""),
    ("Profile views (optional)", "Whole number", "Also accepted: Profile visits."),
]
ARTICLE_GUIDE = "Plain text (paste the article body), at least 40 words, ideally 200-1,500 words. Add the source (author, publication or link) so the post credits it."
JD_GUIDE = "Plain text of one job description (paste the whole posting), at least 60 words."


def _int(v, lo=0, hi=10_000_000):
    try:
        n = int(str(v).strip())
    except (TypeError, ValueError):
        return None
    return n if lo <= n <= hi else None


def validate_profile(p: dict) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Errors block saving; warnings do not."""
    e, w = [], []

    def text(key, label, lo, hi, required=False):
        v = str(p.get(key, "")).strip()
        if not v:
            if required:
                e.append(f"{label} is required.")
            return
        if len(v) < lo:
            e.append(f"{label} is too short (minimum {lo} characters).")
        if len(v) > hi:
            e.append(f"{label} is too long ({len(v)} of {hi} characters).")

    text("name", "Full name", 2, 80, True)
    if p.get("name") and not re.fullmatch(r"[A-Za-z\u00C0-\u024F .'\-()]+", p["name"].strip()):
        w.append("Full name usually contains letters, spaces, dots and hyphens only.")
    for k, lab in (("email", "Email ID"), ("google_email", "Google account")):
        v = str(p.get(k, "")).strip()
        if v and not EMAIL.match(v):
            e.append(f"{lab} does not look like an email address (name@domain.com).")
    url = str(p.get("linkedin_url", "")).strip()
    if url and not LINKEDIN.match(url):
        w.append("LinkedIn URL should look like https://www.linkedin.com/in/your-name")
    text("taplio_account", "Taplio account", 3, 80)
    if " " in str(p.get("taplio_account", "")).strip():
        w.append("Taplio account should be an email or username without spaces (never a password).")
    text("current_role", "Current role", 2, 80, True)
    text("company", "Company", 0, 80)
    text("industry", "Industry / niche", 2, 80, True)
    yrs = str(p.get("years_experience", "")).strip()
    if yrs and _int(yrs, 0, 60) is None:
        e.append("Years of experience must be a whole number from 0 to 60 (digits only).")
    skills = [s.strip() for s in str(p.get("skills", "")).replace("\n", ",").split(",") if s.strip()]
    if not skills:
        e.append("Key skills is required (comma separated).")
    elif len(skills) < 2:
        e.append("List at least 2 skills, separated by commas.")
    elif len(skills) > 20:
        e.append("List at most 20 skills.")
    elif any(len(s) > 40 for s in skills):
        e.append("Each skill must be 40 characters or fewer.")
    text("target_audience", "Target audience", 3, 100, True)
    text("goal", "Main goal", 5, 160, True)
    text("target_roles", "Target roles", 0, 100)
    text("offer", "What you offer", 0, 120)
    if p.get("persona") == "job_seeker" and not str(p.get("target_roles", "")).strip():
        w.append("Job seekers: add Target roles so the headline can say 'Open to ...'.")
    if p.get("persona") == "thought_leader" and not str(p.get("offer", "")).strip():
        w.append("Thought leaders: add What you offer so authority hooks make sense.")
    n = len([x for x in p.get("pillars", []) if x in PILLARS])
    if not 3 <= n <= 5:
        e.append("Choose between 3 and 5 content pillars.")
    nd = len([d for d in p.get("days", []) if d in WEEKDAYS])
    if not 2 <= nd <= 5:
        e.append("Choose between 2 and 5 posting days.")
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", str(p.get("time", ""))):
        e.append("Posting time must be HH:MM in 24-hour format, for example 08:30.")
    if p.get("timezone") not in TIMEZONES:
        e.append("Pick a time zone from the list.")
    try:
        if date.fromisoformat(str(p.get("start_date", ""))) < date.today() and p.get("_enforce_future"):
            e.append("First posting date must be today or later.")
    except ValueError:
        e.append("First posting date must be a valid date (YYYY-MM-DD).")
    for k, lab in (("story_win", "A recent win"), ("story_mistake", "A mistake you learned from"), ("story_lesson", "A lesson")):
        text(k, lab, 0, 400)
    ach = [a for a in str(p.get("achievements", "")).splitlines() if a.strip()]
    if len(ach) > 8:
        e.append("Achievements: at most 8 lines.")
    if any(len(a) > 160 for a in ach):
        e.append("Achievements: keep each line under 160 characters.")
    if ach and not any(re.search(r"\d", a) for a in ach):
        w.append("Achievements read stronger with at least one number (hours saved, % improved, people trained).")
    text("current_headline", "Current headline", 0, 220)
    text("current_about", "Current About section", 0, 2600)
    for line in str(p.get("role_models", "")).splitlines():
        parts = [x.strip() for x in line.split("|")]
        if line.strip() and len(parts) > 1 and parts[1] and not parts[1].lower().startswith("http"):
            w.append(f"Role model '{parts[0]}': the second part should be a web address starting with http.")
    return e, w
