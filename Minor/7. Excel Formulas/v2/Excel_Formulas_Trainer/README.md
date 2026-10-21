# Formula Lab - Excel Formulas

A colourful study app built from your notes. Five screens: Reference, Quiz, Flashcards, Practice and a one-page Revision flowchart. Every screen except the flowchart has a section filter.

## Use it right now
Double-click `index.html`. It works fully in any browser, on laptop or phone, with no setup. Fonts are built in, so it looks the same offline.

## Install it as an app (desktop and phone)
Browsers only offer "Install" for sites served over HTTPS, so put this folder online once:
1. Go to https://app.netlify.com/drop and drag this whole folder onto the page (free, no code). GitHub Pages also works.
2. Open the link it gives you.
3. Desktop (Chrome or Edge): click the install icon in the address bar, or the "Install app" button in the app.
4. Android (Chrome): menu > Install app. iPhone (Safari): Share > Add to Home Screen.

After the first visit the app works offline.

## Files
- `index.html` - the whole app (content, logic, fonts and styles included)
- `Excel_Formulas_Guide.docx` - 11-page guide: flowchart, sample data, quick reference, and a full page of explanation, arguments and examples for every function
- `Revision_Flowchart.png` / `.svg` - the one-page flowchart for quick revision (print it or save it to your phone)
- `manifest.webmanifest`, `sw.js`, `icon-192.png`, `icon-512.png` - install and offline support

## Theme
All deliverables share one palette: Excel green for the main brand, with a colour per section: teal (IFERROR and text), purple (text joins and dynamic arrays), orange (LARGE, SMALL, SUMIFS, FILTER) and pink (XLOOKUP and INDEX MATCH). Yellow highlights every result.
The app uses Fredoka for headings, Nunito for text and JetBrains Mono for formulas. The Word guide uses Trebuchet MS, Calibri and Consolas, the closest fonts that Word has built in.

Your quiz best scores and finished practice tasks are saved in your browser on each device.
