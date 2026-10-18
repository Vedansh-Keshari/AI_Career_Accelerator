# Instructions

Everything you need to run, publish, edit and check the guide. No coding tools are required for steps 1 to 3.

## 1. Run it on your computer

**Easiest:** double-click `index.html`. It opens in your browser and works as it is.

**With a local server** (only needed if you want to open it from your phone on the same Wi-Fi):

```
python3 -m http.server 8000
```

Then open `http://localhost:8000` on the computer. For a phone on the same Wi-Fi, use the computer's local address instead, for example `http://192.168.1.20:8000`. Find it with `ipconfig` (Windows) or `ifconfig` / System Settings (Mac and Linux). Press Ctrl+C in the terminal to stop.

## 2. Put it online (free options)

The site is plain files, so any static host works. Upload the whole folder (keep `css` and `js` inside it).

| Host | Steps |
| --- | --- |
| **Netlify Drop** | Go to app.netlify.com/drop, drag the unzipped folder onto the page. You get a link in seconds. |
| **GitHub Pages** | Create a repository, upload the files, then Settings → Pages → deploy from the main branch. |
| **Vercel** | Import the repository or run `npx vercel` inside the folder. |
| **Any web host** | Upload the files to the public folder with FTP or the host's file manager. |

Share the link under your videos. Chapter links work too, for example `https://your-site/#chapter-4` opens the "One click and AI builds everything" chapter, so you can link each video to its own chapter.

## 3. Check it on your devices

This was tested with automated checks, but not by eye on real phones. Spend two minutes on this before you publish:

1. Open the site on a phone. Tap the menu button (top left), pick chapter 4, and confirm the drawer closes.
2. Tick three steps. Reload the page. The ticks and the percentage should still be there.
3. Open chapter 9 and confirm the yellow "Fix" note shows under the last step.
4. Turn the phone sideways. Nothing should run off the screen.
5. On the laptop, press the right arrow key a few times. Chapters should change.
6. Switch your device to dark mode and reload. Text should stay easy to read.
7. Click "Print guide" and look at the preview. All 11 chapters should appear as a checklist.

If something looks wrong, note which device and browser and fix it in `css/styles.css` (see section 5).

## 4. Edit the content

All text lives in `js/content.js`. Open it in any text editor (Notepad, TextEdit, VS Code).

Each chapter looks like this:

```js
{
  id: 4,
  title: "One click and AI builds everything",
  short: "Build the store",
  type: "action",
  steps: [
    "Atlas is attached inside Shopify → Atlas Dashboard",
    "Amazon → **Carpet** → copy the link",
    { t: "A step with a list", sub: ["First item", "Second item"] },
    { t: "A step that can go wrong", fix: "What to do about it." }
  ]
}
```

- `type: "action"` gives every step a checkbox and counts it in the progress. `type: "overview"` shows plain points.
- Use `**bold**` and `~~strikethrough~~` inside any text. Other formatting is shown as typed.
- Save the file and refresh the browser. There is nothing to build.

**Adding a chapter:** copy a chapter block, give it the next `id` (12, 13, and so on, with no gaps), and put it in the list in the position you want it to appear. If you add an action chapter, the storefront sketch in `index.html` has eight fixed parts (`data-block="2"` to `"10"`), so a new chapter counts toward progress but will not light up its own part of the sketch.

**Changing steps after people have started:** progress is saved by chapter number and step position. If you insert or reorder steps in a chapter, a visitor's ticks can land on the wrong steps. Either add new steps at the end of a chapter, or change `version: 1` at the top of `content.js` to `version: 2`. A new version number makes everyone start fresh.

## 5. Change the look

Open `css/styles.css`. The top of the file lists the colours and fonts as named values:

| Name | What it controls |
| --- | --- |
| `--accent` | Links, focus rings, the main button colour |
| `--ok` | Ticked boxes and progress bars |
| `--tape`, `--tape-soft` | The yellow "Fix" note |
| `--rail-bg`, `--rail-lit` | The dark side panel and the lit parts of the storefront sketch |
| `--canvas`, `--surface`, `--ink` | Page background, panel background, text |
| `--font-display`, `--font-body` | Headings and body fonts |

Dark mode values sit in the `@media (prefers-color-scheme: dark)` block just below. To use your own fonts, change the `<link>` for Google Fonts in `index.html` and the two `--font-` names.

To work fully offline with the same fonts, download them from Google Fonts, put the files in a `fonts` folder, and add `@font-face` rules to the CSS. The site already falls back to system fonts, so this is optional.

## 6. Run the automated tests (optional)

You need Node.js 18 or newer.

```
npm install
npm test
```

You should see 17 passing tests. Run this after any change to `content.js` or `app.js`. It will catch things like a chapter number gap or a broken step list.

## 7. Troubleshooting

| Problem | Fix |
| --- | --- |
| The page is blank or says it needs JavaScript | Enable JavaScript. If you edited `content.js`, check for a missing comma or quote. Open the browser console (F12) to see the line. |
| Ticks are not remembered | The browser is in private mode or blocks site storage. Use a normal window. The guide still works, it just does not save. |
| Ticks moved to the wrong steps | You reordered steps after people started. See "Changing steps after people have started". |
| Fonts look plain | Fonts load from Google Fonts. Offline, or if Google Fonts is blocked, the system font is used. |
| Progress is different on phone and laptop | By design. Progress is saved per device and browser. |
| "Copy chapter text" says copy is blocked | Some browsers block copying on non-secure pages. Publish over https, or select the text manually. |
| I want everyone to start fresh | Change `version` in `content.js`, or use "Reset progress" in the side panel on your own device. |
