"""Everything that differs between the three user paths beyond pillar weights:
navigation, extra KPIs, benefits/setbacks, and the per-phase effects shown in the Persona Lab."""

# --- navigation: each path gets only its targeted tabs -------------------------------------------
PAGES = {
    "command": "🏠 Command Center", "inputs": "🧾 Inputs & Onboarding", "plugins": "🔌 Plugins",
    "phase1": "🧭 Phase 1 · Audit & Pillars", "phase2": "💡 Phase 2 · Ideas & Drafts",
    "phase3": "📅 Phase 3 · Calendar & Taplio", "phase4": "🚀 Phase 4 · Publish & Track",
    "phase5": "📈 Phase 5 · Analytics & Review",
    "hub_professional": "🔁 Consistency Hub", "hub_job_seeker": "🎯 Recruiter Hub", "hub_thought_leader": "🏛️ Authority Studio",
    "persona": "🎭 Persona Lab", "deliverables": "📦 Deliverables & Backups", "docs": "📚 Docs & Help",
}
HUB = {"professional": "hub_professional", "job_seeker": "hub_job_seeker", "thought_leader": "hub_thought_leader"}
CORE_BEFORE = ["command", "inputs", "plugins", "phase1", "phase2", "phase3", "phase4", "phase5"]
CORE_AFTER = ["persona", "deliverables", "docs"]


def nav_keys(persona: str) -> list[str]:
    """Tabs this path sees. Other paths' hubs are not shown at all."""
    return CORE_BEFORE + [HUB[persona]] + CORE_AFTER


# --- path-specific weekly KPIs (Phase 4 log, Phase 5 targets). Targets are 6-week totals ------------
KPI_FIELDS = {
    "professional": [
        {"key": "a", "label": "Profile visits (week)", "help": "Whole number >= 0. LinkedIn > Analytics > Profile viewers.", "target": 150},
        {"key": "b", "label": "Peer comments you made", "help": "Whole number >= 0. Comments you wrote on other people's posts.", "target": 70},
        {"key": "c", "label": "New relevant connections", "help": "Whole number >= 0. Peers or leaders in your niche who accepted you.", "target": 40}],
    "job_seeker": [
        {"key": "a", "label": "Recruiter messages", "help": "Whole number >= 0. DMs or InMails from recruiters this week.", "target": 6},
        {"key": "b", "label": "Connection requests from recruiters / hiring managers", "help": "Whole number >= 0.", "target": 12},
        {"key": "c", "label": "Interview invitations", "help": "Whole number >= 0. Calls or interviews you were invited to.", "target": 3}],
    "thought_leader": [
        {"key": "a", "label": "Followers gained", "help": "Whole number >= 0. Net new followers this week.", "target": 150},
        {"key": "b", "label": "Inbound leads", "help": "Whole number >= 0. People who asked about your work or offer.", "target": 6},
        {"key": "c", "label": "Collaboration / speaking invitations", "help": "Whole number >= 0.", "target": 2}],
}

BENEFITS = {
    "professional": ["Steady credibility inside your niche with a balanced mix of five pillars.",
                     "Low-pressure rhythm (Tue/Wed/Thu) that is easy to keep for six weeks.",
                     "Peer engagement habit builds a network that compounds over time.",
                     "Works for any career stage, so it is a safe default."],
    "job_seeker": ["Fastest route to recruiter attention: proof-of-work posts plus a profile tuned for search.",
                   "Tracks outcomes that matter to you: recruiter messages, interview invitations.",
                   "Ready-made outreach templates and a job-description keyword matcher.",
                   "Open-to-Work and Featured-section guidance built into the audit."],
    "thought_leader": ["Builds authority: debate-style hooks, series and carousels drive shares and follows.",
                       "Inbound leads and collaboration invitations are tracked, not guessed.",
                       "Series planner keeps a recognisable, repeatable voice.",
                       "Carousel studio turns ideas into save-worthy assets."],
}
SETBACKS = {
    "professional": ["Results are slower and broader: no single outcome (jobs, leads) is optimised.",
                     "A balanced mix can feel generic unless you add real examples.",
                     "Needs six or more weeks of consistency before the trend is visible."],
    "job_seeker": ["More personal exposure: be mindful of what your current employer can see.",
                   "Less emphasis on opinions, so authority builds more slowly.",
                   "Personal-story posts need real examples; placeholders hurt credibility.",
                   "Outcomes also depend on the hiring market, not only on your content."],
    "thought_leader": ["Needs a clear point of view and regular time; contrarian takes carry reputation risk.",
                       "Carousels need design effort outside this app.",
                       "Small audiences convert slowly; lead numbers can stay low for weeks.",
                       "Heavier posting rhythm on a weekend slot may not fit everyone."],
}

# --- what changes, phase by phase, when you switch path (Persona Lab) ---------------------------------
PHASE_EFFECTS = {
    "phase1": {
        "professional": "Audit rewards contact info / call to action and posting cadence. Headline: role at company | helping audience | skills.",
        "job_seeker": "Audit rewards Open to Work, Featured proof, recommendations and numbers. Headline ends with Open to <target roles>.",
        "thought_leader": "Audit rewards Creator mode / Follow button and authority content. Headline: offer | helping audience | writing on topic."},
    "phase2": {
        "professional": "Discussion CTAs; mix of text, micro-story, poll and carousel; balanced hooks.",
        "job_seeker": "Recruiter-friendly CTAs (open to roles); proof-of-work and job-search stories; more tips and personal journey.",
        "thought_leader": "Debate CTAs; contrarian and framework hooks; carousel-heavy rotation; series planning."},
    "phase3": {
        "professional": "Posting days Tue / Wed / Thu; weekday-morning rhythm.",
        "job_seeker": "Posting days Mon / Wed / Fri to stay visible through the working week.",
        "thought_leader": "Posting days Tue / Thu / Sat; weekend slot for long-form carousels."},
    "phase4": {
        "professional": "Weekly log: profile visits, peer comments made, new connections.",
        "job_seeker": "Weekly log: recruiter messages, recruiter connection requests, interview invitations.",
        "thought_leader": "Weekly log: followers gained, inbound leads, collaboration invitations."},
    "phase5": {
        "professional": "KPI targets on visits, engagement habit and network growth; consistency streak insights.",
        "job_seeker": "KPI targets on recruiter messages and interviews; profile-visit-to-message conversion insight.",
        "thought_leader": "KPI targets on followers, leads and invitations; shares-to-follower insight."},
}

HUB_FEATURES = {
    "professional": ["Consistency dashboard: planned vs logged, streak, longest gap", "Daily peer-engagement plan (5 comments) with comment starters", "Peer engagement log"],
    "job_seeker": ["Job-description keyword matcher against your profile and drafts", "Opportunity tracker (saved to offer)", "Recruiter outreach templates"],
    "thought_leader": ["Lead and audience tracker", "Series planner with episode hooks", "Carousel studio with slide export"],
}
PRIMARY_DELIVERABLES = {
    "professional": ["calendar", "review"],
    "job_seeker": ["audit", "taplio"],
    "thought_leader": ["dashboard", "capstone"],
}
