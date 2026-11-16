# AI Resume Analyzer: Guide and App

Two ready-to-use pages built from one codebase, so they always match.

- `dist/website.html`: the interactive guide (six Swagger-style steps, tasks, "Try it out" tools, quizzes, progress bar)
- `dist/app.html`: the dashboard (score candidates, charts, search, filter, CSV export, prompt builder, sheet templates)

Open either file in a browser. No install, no internet needed. Keep both files in the same folder so the top bar links work.

## How they stay in sync
Both pages import the same files in `src/shared/` (steps, scoring logic, prompt builder, UI). Progress, settings and candidates are stored under one key in the browser, so a candidate added in the guide appears in the app.

## Using it (manual path: Google Sheets + ChatGPT or Claude)
1. Copy the sheet headers into two Google Sheets.
2. Copy a resume's text. Paste the system prompt and then the resume into a new ChatGPT or Claude chat.
3. Paste the JSON reply into Execute. Add to the dashboard or copy the row into your sheet.

Scoring bands (Strong 80+, Potential 65 to 79, Weak below 65) and the points per parameter are editable in the prompt builder.

## Rebuild after editing
`npm install` then `npm run build`. Edit shared content in `src/shared/content.js`.
