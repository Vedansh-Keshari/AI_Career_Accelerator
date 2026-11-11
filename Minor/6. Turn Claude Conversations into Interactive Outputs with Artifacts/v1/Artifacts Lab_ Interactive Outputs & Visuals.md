ArtifactsLab

[Overview](#home) [Assignments](#assignments) [Calendar app](#calendar)

Course companion

# Claude Artifacts: interactive outputs & visuals

Seven completed assignments, arranged from beginner to advanced, built from the prompts in your notes. Each one shows the prompt, the finished output and, where it helps, a table or chart.

7

assignments completed

4

levels, beginner to advanced

1

working calendar app

## When an artifact is the right choice

| Use it for | Why |
| --- | --- |
| Lengthy content (15+ lines) | Lives in its own window beside the chat |
| Self-contained work | Understandable without the conversation |
| Content you will iterate on | Version history lets you compare changes |
| Reference material | Copy, download, or add to project knowledge |

## Learning path

| Level | Assignments | Skill |
| --- | --- | --- |
| 1 Beginner | A1–A2 | Document artifacts |
| 2 Foundation | A3 | Code artifacts |
| 3 Intermediate | A4–A6 | Charts and SVG visuals |
| 4 Advanced | A7 | Interactive apps |

[Start the assignments](#assignments)

# Assignments

Related prompts are grouped together. Fictional product: the Techmaster X1000 smartphone.

## Level 1: Beginner

Document artifacts

A1

### Product description

> Create a brief product description for a fictional smartphone called Techmaster X1000 as an artifact.

**Techmaster X1000.** A flagship built for people who work from anywhere. A 6.7-inch adaptive display stays crisp in sunlight, a two-day battery outlasts your schedule, and the on-device assistant drafts, summarises and translates without a connection. A pro-grade triple camera and an aluminium frame complete a phone that feels as sharp as it performs.

A2

### Is it better than its competitors?

> Explain whether the Techmaster X1000 is better than its competitors.

| Feature | Techmaster X1000 | Rival A | Rival B |
| --- | --- | --- | --- |
| Battery life | Two days | 1.5 days | 1 day |
| Display | 6.7" adaptive | 6.5" fixed | 6.8" adaptive |
| On-device AI | Yes | Cloud only | Limited |
| Price tier | Premium | Premium | Mid |

**Verdict:** it leads on battery and AI, so it suits heavy mobile workers best. Rival B wins for buyers on a tighter budget. (All figures are illustrative.)

## Level 2: Foundation

Code artifacts

A3

### Fibonacci function

> Create a python function that calculates the Fibonacci sequence, up to a given number and present it as a code artifact.

```
def fibonacci(limit):
    """Return every Fibonacci number up to and including limit."""
    if limit < 1:
        return [0]
    seq = [0, 1]
    while seq[-1] + seq[-2] <= limit:
        seq.append(seq[-1] + seq[-2])
    return seq

print(fibonacci(100))  # [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
```

Try it (limit):

## Level 3: Intermediate

Visual artifacts

A4A5

### Quarterly sales, then profit margin

> Create a simple bar chart showing quarterly sales for a fictional Techmaster X1000 smartphone. Include profit margin in this visualization as well.

Q4 is the strongest quarter for both revenue and margin. Q3 dipped on both. Figures are fictional.

A6

### Product roadmap (SVG)

> Create an SVG image of a simplified product roadmap for our Techmaster smartphone timeline.

SVG stays crisp at any size and drops straight into slides or web pages.

## Level 4: Advanced

Interactive artifacts

A7

### Interactive content calendar, November 2026

> Create an interactive content calendar for November 2026 where a user can click a date, add a post title, choose a department (Marketing, Sales, Product) and save it. Colour-code departments, equal tiles, full page width and height, with example entries.

Completed as a working app: click any date to add or remove posts, and change department colours from the legend.

[Open the calendar app](#calendar)

# November 2026

Sun

Mon

Tue

Wed

Thu

Fri

Sat