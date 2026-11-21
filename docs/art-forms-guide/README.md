# The brief2mp4 art forms guide

[`brief2mp4-art-forms.pdf`](brief2mp4-art-forms.pdf) is a companion guide to the art forms in brief2mp4: the three rules behind every look, how to choose one from a brief, a half-page recipe for each of the 82 forms, and the tools by name.

It is built from editable sources in this folder. The art-form pages come from `plugin/skills/brief2mp4/references/art-forms.json`, so the guide cannot drift from the skill.

| File | What it is |
|---|---|
| `build.py` | the prose and the assembly; writes `brief2mp4-art-forms.html` and `guide-prose.txt` |
| `guide.css` | the print stylesheet |
| `render.py` | HTML to PDF with WeasyPrint, then checks page count, contents links, text inside every page and metadata |
| `img/` | one 640 px frame per demo (82), made from `node tests/art_forms/check_looks.mjs --frames <dir>` and saved as JPEG, plus `_overview.jpg`, the contact sheet from `--sheet img/_overview.jpg --cols 10 --tile 240` |
| `fonts/` | Inter and Space Grotesk (SIL Open Font License 1.1) and DejaVu Sans Mono, each with its licence text |

```bash
python3 -m venv .venv && .venv/bin/pip install -r docs/art-forms-guide/requirements.txt pillow
.venv/bin/python docs/art-forms-guide/build.py
.venv/bin/python docs/art-forms-guide/render.py --sheets
```

WeasyPrint needs the Pango libraries: `brew install pango` on macOS, `sudo apt install libpango-1.0-0 libpangoft2-1.0-0` on Debian or Ubuntu.
