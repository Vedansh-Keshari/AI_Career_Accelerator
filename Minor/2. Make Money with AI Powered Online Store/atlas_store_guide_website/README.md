# Shopify + Atlas: AI store guide

A step-by-step companion website for the video series "Make Money with AI Powered Online Store". It turns the 11 scripted sections into a guide viewers can follow while they build their own Shopify store with the Atlas AI builder.

It works on phones, tablets and desktops, needs no install, and keeps each visitor's progress on their own device.

## What you get

- **11 chapters** taken from your script, in the same order as the videos.
- **Tick-off checklist.** The 8 hands-on chapters have checkable steps (45 in total). The 3 overview chapters (trailer, the plan, closing) are read-only.
- **A storefront sketch** in the side panel that fills in as chapters are completed.
- **Saved progress** in the visitor's browser. It survives refreshes and restarts.
- **Fix callout** for the bundle error in chapter 9 (the "All products" conflict).
- **Copy chapter text**, **Print guide** (whole guide as a plain checklist) and **Reset progress**.
- **Mobile layout** with a slide-out chapter list and a progress bar along the top.
- **Light and dark mode** that follow the device setting, keyboard navigation (left and right arrow keys move between chapters) and reduced-motion support.

## Quick start

1. Unzip the package.
2. Double-click `index.html`.

That is all. There is no server, build step or dependency. To put it online or open it on a phone, see [INSTRUCTIONS.md](INSTRUCTIONS.md).

## What is in the package

| File | Purpose |
| --- | --- |
| `index.html` | The page |
| `css/styles.css` | All styling (colours and fonts are variables at the top) |
| `js/content.js` | **The guide text.** Edit this to change any chapter or step |
| `js/app.js` | The behaviour: navigation, progress, saving, print, copy |
| `README.md` | This overview |
| `INSTRUCTIONS.md` | How to run, publish, edit and customise |
| `REQUIREMENTS.md` | What the site must do, and how that was checked |
| `tests/smoke.test.js`, `package.json` | Optional automated tests (17 checks) |

## About the content

The text comes from your script. These changes were made so it reads cleanly on screen:

- Chapter titles were tidied (for example "Don-t" became "Don't", capital-heavy titles became sentence case).
- "ai" and "Ai" were written as "AI" throughout.
- Sentences were lightly smoothed (for example "login" became "log in"). The steps, order and meaning are unchanged.
- Your `~strikethrough~` and `**bold**` marks are kept: "coding", "designer", "product photos" and "demo" appear struck through in the trailer, and **Carpet** appears in bold in chapter 4.
- The bundle conflict note in chapter 9 is shown as a highlighted "Fix".

## Browser support

Designed for current versions of Chrome, Edge, Firefox and Safari (desktop, Android and iOS) using only widely supported features. See the note in REQUIREMENTS.md about checking it on your own devices before publishing. Fonts load from Google Fonts when online and fall back to system fonts when offline.

## Tests

```
npm install
npm test
```

Runs 17 automated checks covering content, rendering, progress saving, navigation, the mobile drawer, copy and print. They are optional: the site itself has no dependencies.
