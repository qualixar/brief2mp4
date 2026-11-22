# Film mode: one brief to a narrated explainer or documentary

Film mode turns one brief into a finished narrated video of one to ten minutes: an explainer, a short documentary, a history piece. It writes every stage to a file you can open, so you can read the story, the script with a source for each line, the storyboard, the credits for every picture, the measured voice timings and the checks. Nothing is hidden inside a prompt.

The agent drives it for you when your brief asks for a narrated explainer or documentary. This guide shows what happens underneath, so you can steer it, re-run one stage, or run it by hand. The agent's own reference is the section "Explainer and documentary (film mode)" in [references/formats.md](../plugin/skills/brief2mp4/references/formats.md#explainer-and-documentary-film-mode).

## What you get

- `final.mp4`: 1920x1080, H.264 and AAC, -14 LUFS, cut to the measured voice.
- `final.srt`: word-timed captions from the same timings.
- `REPORT.md`: every check, every picture's credit (CC BY credits first, because they belong in the video description), every line without a source, and what is still open.
- The working files of every stage, listed below.

The look is the **archive desk**: a dark editorial page with one still or map as a plate that pushes in slowly, a serif caption under it, a date stamp, a counter that lands on the number as it is spoken, and the picture's credit. For another look, see "A different look" at the end.

## A run you can try in a minute

This is the run used to check this guide: a 20-second brief, four script lines, no picture downloads, the stand-in voice and a draft render. On an Apple M-series laptop every stage from the script to the report took under 20 seconds, and the delivery check passed.

```bash
SKILL=/path/to/brief2mp4/plugin/skills/brief2mp4      # your clone, or the installed skill folder
mkdir my-film && cd my-film
cat > BRIEF.md <<'EOF'
# How undersea cables carry the internet

Make a 20-second explainer on how undersea cables carry the internet, documentary look, stand-in voice for the draft.

audience: people who use the internet every day
takeaway: nearly all intercontinental data travels under the sea
EOF
python3 $SKILL/scripts/film.py story --project .      # writes STORY.md: read it, edit it
```

Then write `SCRIPT.md` (the format is below; in normal use the agent writes it from `STORY.md` and you read it):

```markdown
# Script
pace: 150
format: documentary

## L01
say: Nearly all intercontinental data swims.
screen: UNDER THE SEA
source: https://example.org/cables
date: MARCH 1931

## L02
say: One cable runs from Alexandria to Aswan.
screen: ALEXANDRIA TO ASWAN
source: https://example.org/egypt
visual: map
region: Egypt
point: Alexandria=31.20,29.92
point: Aswan=24.09,32.90
route: Alexandria>Aswan

## L03
say: About one point four million kilometres lie on the seabed.
screen: ON THE SEABED
source: https://example.org/length
count: 0 -> 1400000 | km of cable

## L04
say: That is how the internet crosses an ocean.
screen: HOW IT CROSSES
source: none (no factual claim)
```

The example.org addresses are placeholders for this test only: a real script cites the page each fact comes from.

```bash
python3 $SKILL/scripts/film.py run --project . --from script --no-fetch --quality draft
```

The output names each stage and ends every one with a `PASS`, `WARN` or `FAIL` line. A `FAIL` says what to do and stops the run. For a real film, drop `--no-fetch` so the assets stage looks for licensed pictures, record your voice (see Voice), and render with `--quality delivery`.

## The brief

A brief is free text. A few `key: value` lines are read as they are: `title`, `audience`, `takeaway`, `length`, `format`, `look`, `voice`, `pace`. The rest is read for a length ("3-minute", "90 seconds"), a format (documentary, explainer, product, story), a voice ("my voice", "take.wav") and a pace. `STORY.md` is a scaffold written from it: the logline, the audience, the one takeaway, the act structure with times, and the pace. Edit it freely. `film.py` never overwrites an edited `STORY.md` unless you pass `--force`.

The structure scales with the length. For three minutes it is a hook in the first 5 seconds, a setup, three beats that each add one picture or map and at most one number, a turn that re-hooks the viewer, and a payoff held still at the end. A new visual idea arrives every 8 to 15 seconds.

## The script: every line carries its source

`SCRIPT.md` has a few header lines (`pace` in words a minute, `format`), then one block per narration line:

| Field | What it holds |
|---|---|
| `## L01` | the line's id |
| `say:` | the words spoken |
| `screen:` | the words shown, kept apart from the narration |
| `source:` | a URL with a host for every factual line. `none (no factual claim)` exempts a line that states nothing checkable, and REPORT.md lists it so a reader can disagree. A line with no source is UNVERIFIED |
| `visual:` | `archive`, `map`, `counter` or `title` |
| `query:` or `asset:` | what to search for, or a picture you already have |
| `date:` | the date stamp |
| `beat:` | lines with the same number share one screen |
| `region:`, `point:`, `route:` | a map: `point: Name=lat,lon`, `route: A>B` |
| `count:` | a counter: `count: 0 -> 1400000 | km of cable` |

The render refuses UNVERIFIED lines. Cut the line, add its source, or pass `--allow-unverified` for a draft you will not publish.

## The stages

Each stage reads the files the one before wrote. Any stage can be skipped or run again alone.

| Stage | Writes | What happens |
|---|---|---|
| `story` | `STORY.md` | the scaffold above |
| `script` | (checks `SCRIPT.md`) | counts lines, estimates the spoken length at the pace, lists lines with no source |
| `storyboard` | `STORYBOARD.json` | one entry per beat: its lines, kind (archive, map, counter, title), camera move, transition, sound cues, acts (one act per 45 s by default, `--acts N`) |
| `assets` | `ASSETS.json`, `assets/` | pictures, maps, sound effects and music, each with source, author, licence and attribution text |
| `voice` | `TIMINGS.json`, `audio/lines/` | one WAV per line with its measured length and word times |
| `retime` | `STORYBOARD.json` | beat lengths rewritten from the measured voice |
| `build` | `project/` or `project_acts/` | the archive desk as HyperFrames projects, one per act |
| `captions` | `final.srt`, `captions.json` | 2 to 7 words per caption, timed to the words |
| `mix` | `audio/mix.wav`, `audio/stems/` | voice, ducked music and effects |
| `render` | `final.mp4` | acts render side by side, are joined without re-encoding, then finished |
| `check` | `checks.json`, `checks/` | delivery, seams at the act joins, layout, placeholder text, one still per beat |
| `report` | `REPORT.md` | checks, credits, unsourced lines, open items |

```bash
python3 $SKILL/scripts/film.py --list                                  # the stages
python3 $SKILL/scripts/film.py run --project my-film                   # all of them
python3 $SKILL/scripts/film.py run --project my-film --from retime     # from one stage on
python3 $SKILL/scripts/film.py run --project my-film --skip assets,render
# one stage alone
python3 $SKILL/scripts/film.py voice --project my-film --voice take --take take.wav
```

## Pictures, maps and sound, with licences you can publish

- **Archive pictures** come from Wikimedia Commons and Openverse through `fetch_archive.py`, which keeps only public domain, CC0 and CC BY. ShareAlike, NonCommercial, NoDerivatives and unknown licences are rejected in the request and again on every answer, so a server that ignores the filter changes nothing. Each download is checked to be a real PNG, JPEG or WebP, capped at 25 MB, and recorded with its source URL, author, licence, attribution text and SHA-256. Public domain is as the host tags it, which differs by country, so check the source page before a commercial release. A beat with no licensed picture becomes a typeset title beat: film mode never invents archive footage.
- **Maps** come from `make_map.py`: a country, several countries, a continent, the world or a bounding box, with markers, labels and routes, as SVG. The boundaries are Natural Earth (public domain), shipped as a 54 KB subset so maps work offline. Natural Earth draws borders by who controls the ground; for a disputed region, check what is acceptable where the video will be shown, or pass your own outline with `--geojson`.
- **Sound effects** come from `sfx_synth.py`: whoosh, tick, thud, paper, typewriter, riser and hit, made in code from a seed, so there is nothing to license and no white noise under the voice.
- **Music** is your own licensed track (`--music bed.mp3`), a CC0 or CC BY track found by `fetch_music.py` (`--music-query "calm piano"`) with an `ATTRIBUTION.md`, or MusicGen if you installed it (`--musicgen "prompt"`). MusicGen's weights are CC BY-NC, so its output is non-commercial.

Each piece works on its own too:

```bash
python3 $SKILL/scripts/fetch_archive.py search "submarine cable ship" --kind photo
python3 $SKILL/scripts/fetch_archive.py download "submarine cable ship" --pick 1 \
  --out-dir assets/archive --assets ASSETS.json
python3 $SKILL/scripts/make_map.py --region Egypt \
  --point "Alexandria=31.20,29.92" --point "Aswan=24.09,32.90" \
  --route "Alexandria>Aswan" --out assets/maps/egypt.svg
python3 $SKILL/scripts/sfx_synth.py all --out-dir assets/sfx --seed 7
```

## Voice

| `--voice` | What it is | Use it for |
|---|---|---|
| `standin` | a buzz that follows the words | drafts: it proves timing, captions and loudness, not a finished film |
| `take` | your own recording, `--take take.wav` | the real film |
| `f5-tts` | F5-TTS, if you installed it: `--ref-audio` (a clean 5 to 12 s clip) and `--ref-text` | a generated voice. Its code is MIT, but its pre-trained models are CC BY-NC, so the output is non-commercial, and clone a voice only with the right to do so |

To record a take, read the script lines in order with a clear pause between them. `split_takes.py` cuts the recording at the pauses. When the pauses are too short or too alike, it uses word timings instead (`--words words.json` from `npx hyperframes transcribe`, or a local whisper.cpp model with `--model`), and each cut goes to the quietest point between two lines.

The voice is never time-stretched. The picture is re-timed to it: the `retime` stage leaves 0.30 s before the first word, 0.30 s between lines, 0.45 s between beats and 0.80 s between acts, holds the last frame 1.8 s, and keeps every beat on screen for at least 2 seconds and long enough to read its words. With a beat grid from `beat_grid.py` (`--grid`), each cut moves later, up to `--snap-max` seconds, onto the next music beat, so the voice only ever gets a longer pause.

## Mix, captions and render

`mix.py` places each voice line to the sample, pins every effect by its peak rather than its start, sets the music 7 dB under the voice and ducks it a further 8 dB under each line (15 dB in all), and normalises the sum to -14 LUFS with a true peak under -1.5 dBTP. The stems are saved next to the mix, so a claim such as "the music sits 15 dB under the voice" can be measured on them.

Captions go to `final.srt` for the platform's own caption track. `--burn-captions` draws them into the picture instead, and drops the credit line to keep the page to four text blocks.

The render splits the film into acts that render side by side (12 Chrome workers shared between them, at most 8 each; `--workers` changes it), joins them, and finishes the file with `finish.sh`. `--quality draft` is fast; `--quality delivery` is for the file you publish.

## Checks

The `check` stage runs `check_delivery.sh` at the exact duration, including the seams at each act join; `check_clutter.py` on each page (at most four text blocks, 24 px between them, nothing past the frame edge); `ocr_sweep.sh` on the finished frames for placeholder text and leaked file paths; and `contact_sheet.sh` for one still per beat. Look at the contact sheet before you call the film done. A frozen-stretch WARN on a held title or the final message is expected; the report says so.

## A different look

Film mode builds the archive desk. For another look (watercolour, paper cut-out, a hologram HUD, any of the [82 art forms](../plugin/skills/brief2mp4/references/art-forms.md)), build those beats by hand in HyperFrames, and still use `retime`, `mix`, `render` and `check` from `film.py`, so the voice timing, the mix and the checks stay the same. The archive desk's layout and markup are described in [templates/film/README.md](../plugin/skills/brief2mp4/templates/film/README.md).
