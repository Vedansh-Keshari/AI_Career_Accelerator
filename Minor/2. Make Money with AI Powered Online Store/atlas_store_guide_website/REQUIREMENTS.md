# Requirements

## 1. Purpose

Give viewers of the "Make Money with AI Powered Online Store" video series a single place to follow along: the 11 scripted sections as readable chapters, with a checklist so they can see how far they are in building their Shopify store with Atlas.

## 2. Why a website

The source is a script made of short, ordered sections with steps. That is reading and following material, not a tool that computes or stores data. A website fits because:

- It opens on any phone or computer with no install, which covers the "both mobile and desktop" need.
- A link can be shared under a video or in a description.
- It needs no account, server or database.

A native or desktop app would add installation, updates and separate versions for each platform without adding anything the content needs.

## 3. Users

| User | Need |
| --- | --- |
| Viewer following a video on one screen and the guide on another (often phone beside laptop) | Find the chapter, tick steps, come back later without losing place |
| Creator maintaining the series | Change the wording or add chapters by editing one file, with no build tools |

## 4. Functional requirements

| ID | Requirement |
| --- | --- |
| FR-1 | Show all 11 chapters from the script, in order, with a chapter list always reachable. |
| FR-2 | Mark chapters 2, 4, 5, 6, 7, 8, 9 and 10 as action chapters: every step has a checkbox. |
| FR-3 | Mark chapters 1, 3 and 11 as overview chapters: plain points, no checkboxes, not counted in progress. |
| FR-4 | Show overall progress (percentage and "x of 45 steps") and per-chapter progress (count in the chapter list and a bar in the chapter). |
| FR-5 | Save progress on the visitor's device and restore it on the next visit, including the last chapter viewed. |
| FR-6 | Open a specific chapter from a link (`#chapter-N`). An invalid link opens the last viewed chapter, or chapter 1. |
| FR-7 | Move between chapters with Previous and Next links and the left and right arrow keys. |
| FR-8 | Offer "Mark all steps done" and "Clear all steps" for the current chapter. |
| FR-9 | Offer "Reset progress" for everything, with a confirmation. |
| FR-10 | Offer "Copy chapter text" that puts the chapter on the clipboard as plain text. |
| FR-11 | Offer "Print guide" that prints the whole guide as a checklist, showing which steps are done. |
| FR-12 | Show the nested list in chapter 5 (12 product page elements) under its step. |
| FR-13 | Show the chapter 9 bundle conflict as a highlighted "Fix". |
| FR-14 | Show the script's strikethrough and bold marks (trailer, and **Carpet** in chapter 4). |
| FR-15 | Show a storefront sketch whose parts fill in as the matching chapters are completed. |
| FR-16 | The creator can change all text by editing `js/content.js` only. |

## 5. Non-functional requirements

| ID | Requirement |
| --- | --- |
| NFR-1 | **Works offline from a file.** Opening `index.html` directly must work. No server, build step or package install is needed to run the site. |
| NFR-2 | **Responsive.** Usable from 320 px wide phones to wide desktops. Under 900 px the chapter list becomes a slide-out drawer opened from the top bar. |
| NFR-3 | **Touch friendly.** Tap targets are at least 44 px high. |
| NFR-4 | **Accessible.** Real checkboxes, visible keyboard focus, a skip link, labelled landmarks, announced messages, text contrast of at least 4.5:1 for every main text and background pair in light and dark mode (calculated, not eyeballed), dark mode that follows the device, and reduced motion respected. |
| NFR-5 | **Private.** No tracking, analytics, cookies or accounts. Progress is stored only in the visitor's browser (`localStorage`). |
| NFR-6 | **Resilient.** If storage is blocked or holds corrupt data the site still works, it just does not remember progress. |
| NFR-7 | **Safe text.** Content is escaped before display. Only `**bold**` and `~~strike~~` are interpreted. |
| NFR-8 | **Lightweight.** Three small source files plus the page. No frameworks or libraries. Fonts are the only outside request. |
| NFR-9 | **Browser support.** Current versions of Chrome, Edge, Firefox and Safari on desktop, Android and iOS. |

## 6. Constraints and decisions

- Progress is per browser and per device. It is not synced between a phone and a laptop (that would need accounts and a server).
- Fonts (Bricolage Grotesque, DM Sans) load from Google Fonts. Offline, system fonts are used instead.
- Progress is saved by chapter number and step position. See INSTRUCTIONS.md before reordering steps on a live site.
- The text is the script's text, tidied (see "About the content" in README.md). It does not add new claims.

## 7. Out of scope

Accounts or sign-in, syncing progress across devices, video hosting or embedding, payments, a content management system, and translations.

## 8. Acceptance and how it was checked

Automated checks (`npm test`, 17 tests, all passing) cover:

| Area | Requirements covered |
| --- | --- |
| Content has 11 chapters in order, 8 action chapters, 45 steps | FR-1, FR-2, FR-3 |
| Overview chapter has no checkboxes; strike and bold markup render | FR-3, FR-14, NFR-7 |
| Hash links, invalid hash fallback, 12-item nested list, Fix callout | FR-6, FR-12, FR-13 |
| Ticking updates counts, chapter list, sketch and storage | FR-4, FR-15 |
| Progress restored after reload; corrupt storage tolerated | FR-5, NFR-6 |
| Mark all, clear all, 100% overall, reset | FR-8, FR-9 |
| Arrow keys, Previous and Next, first and last chapter edges | FR-7 |
| Mobile drawer opens and closes (button and Escape) | NFR-2 |
| Copy text, print view with checked state | FR-10, FR-11 |
| Page language, viewport, skip link, focus and reduced-motion styles | NFR-4 |

Static checks: the HTML passes an HTML validator, the CSS parses without errors, and the JavaScript passes a syntax check.

**Not checked in a real browser.** The test environment could not run a graphical browser, so the visual layout (spacing, the drawer animation, dark mode colours, the storefront sketch) and support on real phones were not verified by eye. Before publishing, open the site once on a phone and a laptop and walk through the short checklist in INSTRUCTIONS.md, section "Check it on your devices".
