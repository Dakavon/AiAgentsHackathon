# Amtomat slides

`deck.md` is a [Marp](https://marp.app) deck (Markdown to slides).

## Render

**VS Code:** install the "Marp for VS Code" extension, open `deck.md`, use the live
preview, then "Export slide deck" to PDF / HTML / PPTX.

**CLI:**

```bash
# HTML (self-contained, no extra dependencies)
npx @marp-team/marp-cli@latest deck.md -o deck.html

# PDF (needs a local Chrome/Chromium)
npx @marp-team/marp-cli@latest deck.md --pdf -o deck.pdf

# PowerPoint
npx @marp-team/marp-cli@latest deck.md --pptx -o deck.pptx
```

## To do before presenting

- Replace the "It works today" slide with a screenshot of the live Status chat.
- Adjust the team/credits on the closing slide.
