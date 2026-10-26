# Canvas Studio

A Canva-style maker for **presentations, documents and logos**, built from the three scenarios in
"3 Canva AI Tricks That Save You Hours" (yoga deck, daily-workout blog post, cafe-bookstore logo).
Open an example, or describe your own idea, edit everything, then **push it to your Canva account**.

Two versions share one engine:

```
canva-clone/
  shared/                  <- engine, fonts, example data, config (used by BOTH apps)
  canva-clone-web.zip      <- the website   (unzips to a folder called web/)
  canva-clone-desktop.zip  <- the desktop app (unzips to a folder called desktop/)
```

Unzip both zips **into the same folder that holds `shared/`**, so you end up with
`shared/`, `web/` and `desktop/` side by side. (If you keep them elsewhere, set the
`CANVA_SHARED` environment variable to the path of the shared folder.)

## Start it (Windows)

* Website: open `web`, double-click **run.bat**. Your browser opens at http://127.0.0.1:5000
* Desktop app: open `desktop`, double-click **run.bat**.

The first run creates a private Python environment and installs three small packages
(needs Python 3.10 or newer from python.org; tick "Add Python to PATH"). Mac/Linux: use `run.sh`
(on Linux the desktop app also needs `sudo apt install python3-tk`).

Your projects are saved in `~/.canvas_studio` (shared by both apps, so a project made in one opens in the other).

## Canva connection

Out of the box the apps run in **demo mode**: sign-in and pushes go to a small local stand-in for Canva
(with an email box), so you can try the whole flow immediately. Nothing leaves your computer.

To connect your **real** Canva account:

1. Create an integration at canva.com/developers (Canva account required).
2. Add the redirect URLs `http://127.0.0.1:5000/oauth/callback` (website) and
   `http://127.0.0.1:5001/oauth/callback` (desktop). If Canva refuses plain http for local use, see their
   docs for the current rule on localhost redirects.
3. Enable the scopes: `design:meta:read design:content:read design:content:write asset:read asset:write profile:read`.
4. Copy `shared/config.example.json` to `shared/config.json` and paste your client id and secret.
5. Restart. The chip at the top changes from "Demo Canva" to "Canva". Click it, sign in.

Sign-in uses Canva's official OAuth (with PKCE): you type your email on **Canva's own page** in your browser.
The apps never see or store your Canva password; they keep only the access token on your computer.

## What to know

* **Not affiliated with Canva.** This is an independent tool that talks to Canva's public Connect API.
* **The starter text is template-based, not AI.** "From my idea" builds an editable outline from your words;
  "Refine" understands simple requests (brighter, bolder, bigger text, different colour, a named style, a catchier title).
  Canva's own AI generation is not part of the public API.
* **What a push creates.** Logos and short posts arrive as an image design. Decks and documents arrive as a
  multi-page design imported from a PDF of your pages, so the pages are images (recreate text in Canva if you need to
  edit it). Canva currently marks its design-import API as a preview, so it may change and is meant for private use.
* **Live Canva is untested here.** Everything was tested end to end against the built-in demo Canva, which follows
  Canva's documented endpoints, but I could not sign in to a real Canva account. If your first real push fails, the
  app shows Canva's error message; send it to me and I'll adjust.

## Tests

```
pip install pytest flask pillow requests
python -m pytest shared/tests web/tests -q
xvfb-run -a python -m pytest desktop/tests -q      # Linux; on Windows run without xvfb-run
```
