"""Domain knowledge: personas, content pillars, formats, idea banks, prompt templates.

Everything a non-programmer might want to tweak (wording, weights, hooks) lives here
so the engine modules stay free of content.
"""
from __future__ import annotations

PILLARS = {
    "career_insights": {"label": "Career Insights", "emoji": "🧭", "color": "#7C3AED",
                        "desc": "Hard-won lessons about growth, promotions and decisions."},
    "thought_leadership": {"label": "Thought Leadership", "emoji": "🔥", "color": "#F97316",
                           "desc": "Opinions, frameworks and bets that make people think."},
    "personal_journey": {"label": "Personal Journey", "emoji": "🌱", "color": "#EC4899",
                         "desc": "Honest stories: wins, mistakes and what you are learning."},
    "industry_trends": {"label": "Industry Trends", "emoji": "📡", "color": "#0EA5E9",
                        "desc": "What is changing in your field, explained in plain English."},
    "actionable_tips": {"label": "Actionable Tips", "emoji": "🛠️", "color": "#10B981",
                        "desc": "Checklists, templates and habits people can use today."},
}

FORMATS = {
    "text": {"label": "Text post", "emoji": "📝", "color": "#6366F1"},
    "micro_story": {"label": "Micro-story", "emoji": "📖", "color": "#EC4899"},
    "poll": {"label": "Poll", "emoji": "📊", "color": "#F59E0B"},
    "carousel": {"label": "Carousel", "emoji": "🎠", "color": "#14B8A6"},
}

TONES = ["Professional but relatable", "Warm and encouraging", "Direct and analytical",
         "Playful and witty", "Calm and authoritative"]

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

TIMEZONES = ["Asia/Kolkata", "UTC", "Europe/London", "Europe/Berlin", "America/New_York",
             "America/Chicago", "America/Los_Angeles", "Asia/Dubai", "Asia/Singapore",
             "Asia/Tokyo", "Australia/Sydney"]

# --- the three roles named in the project brief (User Story, Part 4) ---------
PERSONAS = {
    "professional": {
        "label": "Working Professional", "emoji": "💼", "color": "#4F46E5",
        "story": "I want a guided content workflow so that I can post consistently and grow my personal brand.",
        "goal": "Visibility and credibility inside my niche.",
        "weights": {"career_insights": .25, "thought_leadership": .20, "personal_journey": .15,
                    "industry_trends": .20, "actionable_tips": .20},
        "format_cycle": ["text", "micro_story", "text", "poll", "carousel", "text"],
        "kpis": ["Impressions", "Comments", "Profile visits"],
        "ctas": ["What has been your experience? I would love to hear it in the comments.",
                 "How does this show up on your team? Tell me below.",
                 "If you found this useful, share it with a colleague who needs it."],
        "default_days": ["Tuesday", "Wednesday", "Thursday"],
    },
    "job_seeker": {
        "label": "Job Seeker", "emoji": "🎯", "color": "#EC4899",
        "story": "I want to optimize my LinkedIn presence so that I attract recruiters and opportunities.",
        "goal": "Recruiter attention, interviews and inbound opportunities.",
        "weights": {"career_insights": .20, "thought_leadership": .10, "personal_journey": .25,
                    "industry_trends": .15, "actionable_tips": .30},
        "format_cycle": ["text", "micro_story", "carousel", "text", "poll", "text"],
        "kpis": ["Profile visits", "Recruiter messages", "Connection requests"],
        "ctas": ["I am open to {target_roles} roles. If your team is hiring, my DMs are open.",
                 "What would you add to this list? Recruiters and peers, I would value your view.",
                 "If this resonated, let us connect. I am always happy to swap notes."],
        "default_days": ["Monday", "Wednesday", "Friday"],
    },
    "thought_leader": {
        "label": "Thought Leader / Entrepreneur", "emoji": "🚀", "color": "#F97316",
        "story": "I want to scale influence by using AI to generate impactful content aligned with my brand voice.",
        "goal": "Authority, followers, shares and inbound leads.",
        "weights": {"career_insights": .10, "thought_leadership": .30, "personal_journey": .15,
                    "industry_trends": .25, "actionable_tips": .20},
        "format_cycle": ["text", "carousel", "micro_story", "text", "poll", "carousel"],
        "kpis": ["Followers gained", "Shares", "Inbound leads"],
        "ctas": ["Agree or disagree? Tell me why below.",
                 "If this resonated, follow along. I write about {industry} every week.",
                 "What is the one thing you would challenge here? Let us debate it in the comments."],
        "default_days": ["Tuesday", "Thursday", "Saturday"],
    },
}

# --- idea bank: (hook, angle) per pillar -------------------------------------
IDEA_BANK = {
    "career_insights": [
        ("The best career advice I ignored for years (and what finally changed my mind)", "reflective advice"),
        ("Visibility beats busyness: what {years} in {industry} taught me about getting noticed", "career growth"),
        ("Nobody tells {audience} this about moving from junior to senior in {industry}", "myth-busting"),
        ("3 skills that quietly separate good {role}s from great ones", "skills list"),
        ("Why I stopped chasing job titles and started chasing problems", "mindset shift"),
        ("The career move that looked like a step back but was not", "story with lesson"),
        ("How I decide whether a new opportunity is worth a yes", "decision framework"),
        ("What I would tell my first-year self working in {industry}", "letter to past self"),
    ],
    "thought_leadership": [
        ("Unpopular opinion: most {industry} advice about {skill} is outdated", "contrarian take"),
        ("Everyone in {industry} is talking about AI. Few talk about what it will not replace.", "future view"),
        ("Here is what I believe about the future of {role}s, and why I could be wrong", "honest prediction"),
        ("The myth about {skill} that holds {audience} back", "myth-busting"),
        ("A simple framework I use to make better decisions in {industry}", "framework"),
        ("We measure the wrong thing in {industry}. Here is what to track instead.", "metrics critique"),
        ("If I were starting in {industry} today, I would bet on {skill}", "advice with a bet"),
        ("Hot take: consistency beats brilliance in {industry}", "opinion"),
    ],
    "personal_journey": [
        ("My biggest mistake as a {role} (and the lesson I still use)", "mistake"),
        ("A small win this month that reminded me why I chose {industry}", "win"),
        ("How I got my first real break in {industry}", "origin story"),
        ("The moment I realised I needed to get serious about {skill}", "turning point"),
        ("A lesson from a failure nobody saw", "lesson"),
        ("Why I am building my personal brand in public", "why I post"),
        ("What a bad day at work taught me about {skill}", "lesson"),
        ("Something I am learning right now, and I am not good at it yet", "vulnerability"),
    ],
    "industry_trends": [
        ("3 shifts in {industry} that {audience} should watch this quarter", "trend list"),
        ("What the latest wave of AI tools means for {role}s", "AI impact"),
        ("The skill gap in {industry} that nobody is hiring for loudly", "skills gap"),
        ("I read a lot about {industry} this week. Three ideas worth your time.", "curated reading"),
        ("Where {industry} hiring is heading and how to prepare", "hiring outlook"),
        ("A trend in {industry} that looks small today and big in a year", "early signal"),
        ("Tools {audience} are quietly adopting in {industry}", "tool watch"),
        ("What changed in {industry} over the last 12 months, in plain English", "recap"),
    ],
    "actionable_tips": [
        ("5 minutes a day on {skill}: the routine that actually stuck", "habit"),
        ("A simple checklist I use before every {role} deliverable", "checklist"),
        ("How to explain {skill} to a non-expert in 30 seconds", "communication"),
        ("Steal this structure for your next {industry} project update", "template"),
        ("3 mistakes {audience} make with {skill} (and quick fixes)", "mistakes"),
        ("How I structure my week to protect deep work", "productivity"),
        ("The 15-minute habit that improved my {skill} fastest", "habit"),
        ("Do this before you hit send: a quick quality check for {audience}", "checklist"),
    ],
}

PERSONA_IDEAS = {
    "job_seeker": [
        ("actionable_tips", "How I would make a recruiter's job easier when hiring for {target_roles}", "recruiter view"),
        ("personal_journey", "What my job search taught me about telling my own story", "job search lesson"),
        ("career_insights", "The project that best proves I can do {target_roles}", "proof of work"),
        ("actionable_tips", "How I tailor my application for {target_roles} in 20 minutes", "process"),
    ],
    "thought_leader": [
        ("thought_leadership", "What {audience} get wrong about {offer}", "myth-busting"),
        ("industry_trends", "The contrarian bet I am making in {industry}", "bet"),
        ("personal_journey", "Why I started building {offer}", "origin story"),
        ("actionable_tips", "A free playbook: how {audience} can start with {skill} this week", "playbook"),
    ],
    "professional": [
        ("career_insights", "How I earned trust on my team as a {role}", "trust"),
        ("industry_trends", "What my team is quietly changing in {industry} this year", "team view"),
        ("actionable_tips", "A meeting habit that saved my team hours every week", "habit"),
        ("thought_leadership", "The best {role}s I know do one thing differently", "observation"),
    ],
}

# --- body-building blocks -------------------------------------------------
SETUPS = {
    "career_insights": ["I have been thinking about this a lot while working as a {role} in {industry}.",
                        "This is something I wish someone had told me earlier in my career.",
                        "A quick reflection from my own career so far."],
    "thought_leadership": ["I know this will not be popular with everyone, so let me explain.",
                           "I have changed my mind on this over the last year.",
                           "Here is where I have landed, after a lot of thinking."],
    "personal_journey": ["I do not share this often, but it is worth sharing.",
                         "Real talk, since honesty works better than polish.",
                         "Here is the short version of a longer story."],
    "industry_trends": ["I spend a lot of time watching how {industry} is moving. Here is what stands out.",
                        "Three signals I keep seeing across {industry} right now.",
                        "No hype, just what I am noticing."],
    "actionable_tips": ["Saving you the trial and error I went through.",
                        "This takes minutes, and it works.",
                        "Simple, practical, and you can try it today."],
}

POINTS = {
    "career_insights": [
        "Write down what you shipped every Friday. Visibility starts with a record.",
        "Say yes to problems, not titles. Problems build the reputation.",
        "Ask for feedback before the review cycle, not during it.",
        "Find someone two levels above you and learn how they think, not just what they do.",
        "Put numbers on your wins: time saved, errors cut, revenue added.",
        "Build relationships before you need them. It is far easier than it sounds.",
    ],
    "thought_leadership": [
        "The tool matters less than the question you ask it.",
        "Depth in {skill} compounds. Breadth just keeps you busy.",
        "The people who win in {industry} are rarely the loudest. They are the most consistent.",
        "Most problems in {industry} are communication problems wearing a technical costume.",
        "Judgment is the skill that automation makes more valuable, not less.",
        "A clear opinion, shared early, beats a perfect take shared never.",
    ],
    "personal_journey": [
        "Progress rarely looks like progress while it is happening.",
        "The mistake taught me more than the win ever did.",
        "Asking for help earlier would have saved me weeks.",
        "Small, repeated effort beat one big push every single time.",
        "I am still learning this, and that is exactly why I am sharing it.",
        "The people who helped me most did it without being asked.",
    ],
    "industry_trends": [
        "Teams are shifting from owning tools to owning outcomes.",
        "Employers are asking for {skill} alongside the usual job description.",
        "AI is moving from experiment to everyday workflow in {industry}.",
        "Communication and judgment are becoming the differentiators.",
        "The gap between demand for {skill} and people who can actually do it is real.",
        "Smaller, faster experiments are replacing big annual plans.",
    ],
    "actionable_tips": [
        "Pick one thing. Do it for 5 minutes daily for two weeks. Then review.",
        "Write the outcome you want in one sentence before starting any task.",
        "End every update with the decision you need from the reader.",
        "Keep a running list of questions. Answer one every morning.",
        "Teach it to someone else. If you cannot explain it, you do not own it yet.",
        "Block 90 minutes of deep work on your calendar and defend it.",
    ],
}

POLLS = {
    "career_insights": [("What helped your career most?", ["A mentor", "A tough project", "A job change", "Self-study"]),
                        ("What slows career growth the most?", ["Low visibility", "Skill gaps", "No feedback", "Burnout"])],
    "thought_leadership": [("Which matters more in {industry} over the next 3 years?", ["Technical depth", "Communication", "AI fluency", "Domain knowledge"]),
                           ("Will AI make {role}s more or less valuable?", ["More valuable", "Less valuable", "Just different", "Too early to say"])],
    "personal_journey": [("What is your biggest learning source?", ["Mistakes", "Mentors", "Books and courses", "Side projects"]),
                         ("What do you share least on LinkedIn?", ["Failures", "Wins", "Opinions", "Behind the scenes"])],
    "industry_trends": [("Which shift matters most in {industry}?", ["AI tooling", "Remote work", "Skills-first hiring", "Automation"]),
                        ("How fluent is your team with AI tools?", ["Beginner", "Getting there", "Comfortable", "Advanced"])],
    "actionable_tips": [("Which habit would you try first?", ["Weekly wins log", "5-minute practice", "Deep-work block", "Teach-back"]),
                        ("Where do you lose the most time?", ["Meetings", "Context switching", "Unclear tasks", "Email"])],
}

PILLAR_TAGS = {
    "career_insights": ["CareerGrowth", "CareerAdvice"],
    "thought_leadership": ["ThoughtLeadership", "Leadership"],
    "personal_journey": ["PersonalBranding", "LessonsLearned"],
    "industry_trends": ["FutureOfWork", "Trends"],
    "actionable_tips": ["CareerTips", "ProfessionalDevelopment"],
}

INCLUSIVE_REPLACEMENTS = {
    "guys": "everyone / team", "manpower": "workforce", "rockstar": "expert", "ninja": "expert",
    "crazy": "remarkable", "insane": "remarkable", "blacklist": "blocklist", "whitelist": "allowlist",
    "chairman": "chair", "mankind": "humanity", "man-hours": "work hours", "sanity check": "quick check",
    "dumb": "unwise", "crippled": "hindered", "grandfathered": "legacy",
}

# --- prompt templates A-C come straight from the project brief (Part 17) --------
TEMPLATE_A = "Generate 5 engaging LinkedIn post ideas about [industry/career topic]."
TEMPLATE_B = "Rewrite this draft in a professional but relatable tone."
TEMPLATE_C = "Summarize this article into a LinkedIn post with 3 key takeaways."
SYSTEM_PROMPT = (
    "You are a careful LinkedIn ghostwriter. Write in the author's first person, in a natural human voice. "
    "Never invent facts, numbers, employers or quotes. Where a personal detail is needed and unknown, write a "
    "[bracketed placeholder]. Use inclusive, neutral language. Credit any outside source you reference. "
    "Open with a hook under 120 characters. Short paragraphs. At most one emoji. No hashtags inside the body."
)
