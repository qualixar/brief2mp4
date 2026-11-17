#!/usr/bin/env python3
"""build.py: assemble the brief2mp4 art-forms guide as one HTML file (brief2mp4-art-forms.html) and a plain-text
copy of its prose (guide-prose.txt). render.py turns the HTML into the PDF.

Every art-form page is generated from plugin/skills/brief2mp4/references/art-forms.json, so the guide cannot drift
from the skill. Edit the prose here, the look in guide.css.

    python3 docs/art-forms-guide/build.py
"""
import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SKILL = REPO / 'plugin' / 'skills' / 'brief2mp4'
DATA = json.loads((SKILL / 'references' / 'art-forms.json').read_text(encoding='utf-8'))
FORMS = DATA['forms']
E = html.escape


def inline(t):
    t = E(t)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    return re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', t)


def p(*paras):
    return ''.join('<p>%s</p>' % inline(x) for x in paras)


def ul(items):
    return '<ul>' + ''.join('<li>%s</li>' % inline(x) for x in items) + '</ul>'


def table(head, rows, widths):
    return ('<table>' + ''.join('<col style="width:%s">' % w for w in widths) + '<thead><tr>' + ''.join('<th>%s</th>' % inline(c) for c in head)
            + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>%s</td>' % inline(c) for c in r) + '</tr>' for r in rows) + '</tbody></table>')


def code(t):
    return '<pre><code>%s</code></pre>' % E(t.strip('\n'))


def note(title, text):
    return '<aside><b>%s</b>%s</aside>' % (inline(title), p(text))


def cadence(f):
    return '%d changes a second' % f['fps'] if f['fps'] else 'smooth'


SECTIONS = []


def section(sid, title, eyebrow, body, toc=True):
    SECTIONS.append((sid, title, eyebrow, body, toc))


section('what', 'A look is a set of rules', 'Orientation', '<p class="lead">%s</p>' % inline(
    'Ask for "claymation" or "a paper cut-out" and you are asking for a short list of things: how edges look, how light falls, how often the picture changes. '
    'This guide writes those lists down for %d art forms, and shows how to build each one in code that renders the same way every time.' % len(FORMS)) + p(
    'It is a companion to brief2mp4, the skill that turns a written brief into a finished, checked MP4. The skill builds video from web pages: HTML, CSS and GSAP in HyperFrames, '
    'canvas, SVG and Three.js. Every art form here has a reference page in the skill and a small demo that is tested in a real browser.') + '<figure><img src="../../assets/art-forms.jpg" alt=""><figcaption>One frame from each of the 31 demos, drawn by the test that checks them.</figcaption></figure>' + table(
    ['Family', 'Art forms'], [[DATA['families'][k], ', '.join(f['name'] for f in FORMS if f['family'] == k)] for k in DATA['families']], ['24%', '76%']) + note(
    'What the demos are', 'Small pictures that prove a technique: a few seconds, 960 by 540, drawn on a canvas or with Three.js. They are starting points for a scene, not finished films. '
    'No art-form video was rendered through HyperFrames for this guide.'))

section('rules', 'Three rules behind every look', 'The method', '<p class="lead">%s</p>' % inline(
    'A renderer that works frame by frame asks for frame 212, then frame 213, sometimes out of order and on several workers. Three rules make any look survive that.') + '<h2>1. The picture is a function of time</h2>' + p(
    'No clock, no timers, no `Math.random()`. Whatever is on screen at second 4.2 must depend on the number 4.2 and nothing else. Randomness comes from a hash of the frame number or of a position, so it is the same on every run.') + code('''
export function hash(a, b = 0, c = 0) {            // a repeatable number in 0..1 from up to three integers
  let n = (Math.imul(a | 0, 374761393) + Math.imul(b | 0, 668265263) + Math.imul(c | 0, 2147483647)) | 0;
  n = Math.imul(n ^ (n >>> 13), 1274126177);
  return ((n ^ (n >>> 16)) >>> 0) / 4294967295;
}''') + '<h2>2. Handmade looks hold their drawings</h2>' + p(
    'Film runs at 24 frames a second, but clay, paper and hand-drawn animation are usually shot "on twos": each pose is held for two frames, so the picture changes about 12 times a second. '
    'That stepping is most of what makes them read as handmade. Quantise time before posing anything, and leave the video itself at 24 or 30.') + code('''
export const frameOf = (t, fps) => Math.floor(t * fps + 1e-6);   // which drawing we are on
export const held = (t, fps) => frameOf(t, fps) / fps;           // time, quantised
const ts = held(t, 12);                                          // "on twos"
// in GSAP the same idea for one tween:  gsap.to(el, { x: 400, duration: 1, ease: "steps(12)" })''') + p(
    'Clean looks are the opposite: a flat explainer, a low-poly scene, a product render and kinetic type stay smooth at the full frame rate.') + '<h2>3. Imperfection is seeded</h2>' + p(
    'Line boil, paper jitter, lamp flicker, misregistered ink and tape damage all come from one line: a small nudge keyed to the drawing number.') + code('''
export const jit = (frame, i, amount) => (hash(frame, i, 7) - 0.5) * 2 * amount;
const f = frameOf(t, 12);
x += jit(f, partIndex, 1.2);          // this part sits 1.2 px off, differently on each drawing, identically on each render''') + note(
    'The usual web recipe breaks rule 1', 'Most tutorials make a hand-drawn line wobble with a timer that re-rolls an SVG filter every 100 milliseconds. A frame-by-frame renderer has no such timer. '
    'Key the change to the frame number instead, and the wobble is part of the frame.') + '<h2>How the demos are checked</h2>' + p(
    'A test draws every look in headless Chrome at three moments. The three pictures must differ, none may be blank, and the middle one, drawn a second time after the others, must match itself pixel for pixel. '
    'A second test reads the source and fails if a clock, a timer or `Math.random` appears anywhere in it.'))

section('choose', 'Choosing a look from a brief', 'The method', '<p class="lead">%s</p>' % inline(
    'If the brief names a look, use it. If it does not, the subject and the mood usually point to one.') + table(['The brief is about', 'Try', 'Why'], [
        ['children, family, a gentle story', 'paper cut-out, claymation, felt', 'handmade textures feel warm and safe'],
        ['a folk tale, a myth, heritage', 'shadow puppetry, linocut, ink wash', 'the form carries the tradition; check the iconography with a source'],
        ['explaining a product or a process', 'flat vector explainer, isometric, whiteboard', 'clean shapes keep attention on the idea'],
        ['numbers', 'infographic', 'the chart is the picture; every number needs a source'],
        ['a song or a quote', 'lyric video, kinetic typography', 'the words are the content'],
        ['a physical product', '3D product render; claymation for a playful take', 'the object is the hero'],
        ['nostalgia', 'VHS and glitch, pixel art, rubber-hose, UPA mid-century', 'each one is a decade'],
        ['calm, reflective', 'watercolour, ink wash, line art', 'slow, sparse, quiet'],
        ['loud, independent', 'risograph, collage, motion comic', 'print energy and hard cuts'],
    ], ['30%', '34%', '36%']) + code('''
$ python3 plugin/skills/brief2mp4/scripts/art_route.py BRIEF.md
Art form: Shadow puppetry (inferred)
  why: a traditional story: the form carries the tradition ("ramayana")
  cadence: steps 12 times a second
  usual tool: HyperFrames (canvas or SVG)
  note: Use Blender for real light through translucent coloured leather.
  or: Linocut and woodcut print, Ink wash (sumi-e)
  read: references/art-forms/shadow-puppet.md''') + p(
    'The router is a keyword scorer, not a judge. One stray word is never enough ("paper" in "paper plane" does not choose paper cut-out), and when nothing fits it says so. '
    'An art form sets the look and the timing; the kind of video (explainer, Short, launch) still sets the beats.') + '<h2>Writing the look into the brief</h2>' + p(
    'A look becomes checkable when the brief says what should be visible. Two lines are enough:') + code('''
Look: paper cut-out. Flat layers with a small shadow under each, edges that look cut by hand, paper grain.
Done when: at 4.0 s the frame shows at least three paper layers with shadows; the bird's wings
           change at most 12 times a second; nothing moves between drawings.''') + '<h2>Assets</h2>' + p(
    'Most looks here need no pictures at all: shapes, textures and grain are drawn in code. Where a look needs photographs, footage, a character model or music, use only what you own or may reuse. '
    'If you have an image model, it can generate textures and cut-out parts; say in the report that they were generated.'))


def form_block(f):
    img = '<img src="img/%s.jpg" alt="">' % f['looks'][0]
    left = '<div class="pic">%s<h3>Timing</h3><p>%s</p><h3>Assets</h3><p>%s</p><h3>Sound</h3><p>%s</p></div>' % (img, inline(f['timing']), inline(f['assets']), inline(f['sound']))
    mid = '<div><h3>What makes it read as this</h3>%s<h3>What makes it look wrong</h3>%s</div>' % (ul(f['rules']), ul(f['pitfalls']))
    right = '<div><h3>How to build it</h3>%s%s</div>' % (ul(f['build']), ('<p>%s</p>' % inline(f['blender'])) if f['blender'] else '')
    thin = ('<p class="muted small">Sourcing note: %s</p>' % inline(f['thin'])) if f['thin'] else ''
    return ('<div class="style"><div class="fam">%s · %s · %s</div><h2>%s</h2><p>%s %s</p>%s<div class="cols">%s%s%s</div></div>'
            % (E(DATA['families'][f['family']]), E(cadence(f)), E(f['route']), E(f['name']), inline(f['what']), inline(f['origin']), thin, left, mid, right))


LEADS = {'craft': 'Looks that show the hand: real materials, held drawings, small errors.',
         'drawn': 'Looks made of line and paint, from cel animation to ink on paper.',
         'geometry': 'Looks built from blocks, facets and pixels, and the clean studio shot.',
         'type': 'Looks where words, numbers or the recording medium are the picture.'}
for fam, title in DATA['families'].items():
    group = [f for f in FORMS if f['family'] == fam]
    for i in range(0, len(group), 2):           # two forms to a page
        body = ('<p class="lead">%s</p>' % inline(LEADS[fam]) if i == 0 else '') + ''.join(form_block(f) for f in group[i:i + 2])
        section('form-%s-%d' % (fam, i), title, title, body, toc=(i == 0))

section('tools', 'Tools that exist, by name', 'Reference', table(['Where', 'What', 'Used for'], [
    ['SVG filter', '`feTurbulence`', 'noise: grain, the source for every rough edge'],
    ['SVG filter', '`feDisplacementMap`', 'bend a shape by that noise: cut edges, line boil, ink bleed'],
    ['SVG filter', '`feMorphology`', 'thicken or thin: outlines'],
    ['SVG filter', '`feColorMatrix`, `feComponentTransfer`', 'recolour, threshold, separate one ink, sepia'],
    ['CSS', '`steps()`', 'held drawings in a CSS animation'],
    ['CSS', '`mix-blend-mode: multiply`', 'ink printed over ink, paper grain over everything'],
    ['CSS', '`mix-blend-mode: screen`, `plus-lighter`', 'glow that adds up: neon, chroma bleed'],
    ['CSS', '`image-rendering: pixelated`', 'pixel art scaled with hard edges'],
    ['Canvas', '`globalCompositeOperation`', 'the same blends on a canvas, and `destination-out` to cut marks out of a shape'],
    ['Canvas', '`fill("evenodd")`', 'holes that are part of a figure: shadow puppets'],
    ['GSAP', '`ease: "steps(n)"`', 'held drawings in a tween'],
    ['Three.js', '`MeshToonMaterial` with a `gradientMap`', 'light in hard bands: cel shading'],
    ['Three.js', 'a second mesh, larger, back faces only', 'an outline (the inverted hull); `OutlineEffect` packages it'],
    ['Three.js', '`flatShading: true`', 'low-poly facets'],
    ['Three.js', '`InstancedMesh`', 'thousands of voxels in one draw call'],
    ['Three.js examples', '`HalftonePass`, `RenderPixelatedPass`, `FilmPass`, `RGBShiftShader`, `GlitchPass`, `UnrealBloomPass`', 'post-processing for print, pixel, tape and glow looks'],
], ['18%', '40%', '42%']) + p(
    'Three.js ships no watercolour pass and no VHS pass: both are built from the pieces above. Its `GlitchPass` chooses its own random timing, so check that it repeats before relying on it in a render.') + '<h2>When Blender is the better tool</h2>' + ul(
    [f['name'] + ': ' + f['blender'] for f in FORMS if f['blender']]) + '<h2>Wiring a look into a composition</h2>' + code('''
const clock = { t: 0 };
const tl = gsap.timeline({ paused: true });
tl.to(clock, { t: DURATION, duration: DURATION, ease: "none", onUpdate: () => draw(clock.t) }, 0);
window.__timelines = window.__timelines || {};
window.__timelines["main"] = tl;
draw(0);''') + p('GSAP owns the clock and the look only draws. Vendor GSAP and Three.js into the project so a render never touches the network.'))

seen, srcs = set(), []
for f in FORMS:
    for u in f['sources']:
        if u not in seen:
            seen.add(u)
            srcs.append(u)
section('sources', 'Sources and what was verified', 'Reference', '<p class="lead">%s</p>' % inline('What this guide rests on, and where its limits are.') + '<h2>Verified by running it</h2>' + ul([
    'All 31 demos pass the browser test: each paints, changes over time and repeats exactly.',
    'The source of the demos contains no clock, timer or unseeded random call; a test enforces it.',
    'The router and the generated reference pages have unit tests.',
]) + '<h2>Not verified</h2>' + ul([
    'No art-form video was rendered through HyperFrames. The demos follow its rules and were tested as browser pictures.',
    'Tested on macOS with Chrome 157 only.',
    'Frame-rate conventions come from encyclopaedia articles, not from studio production notes.',
    'Lines marked "practice note" in the reference pages (most sound and pacing advice, some visual rules) are working advice, not sourced facts.',
    'Entries with a sourcing note are thinner than the rest: ' + ', '.join(f['name'] for f in FORMS if f['thin']) + '.',
]) + '<h2>Published sources</h2><p class="src">' + '<br>'.join(E(u) for u in srcs) + '</p>' + p(
    'The repositories studied for techniques, with their licences, are listed in the changelog entry and in the project notes. No code from another project is copied into brief2mp4 for this work. Facts were checked on 17 November 2026.'))

toc = ''.join('<a href="#%s">%s</a>' % (sid, E(t)) for sid, t, _, _, in_toc in SECTIONS if in_toc)
cover = '''<section class="cover"><div class="eyebrow">Qualixar<span>Companion guide · November 2026</span></div>
<h1>brief<i>2</i>mp4</h1><div class="deck">The art forms guide</div>
<div class="strap">%d looks for animated video, and how to build each one in code that renders the same way twice.<br>Claymation · paper cut-out · shadow puppetry · anime · watercolour · ink · risograph · pixel art · voxel · VHS · neon</div>
<img class="mark" src="../../plugin/assets/icon.png" alt="">
<div class="by">Varun Pratap Bhardwaj · github.com/qualixar/brief2mp4 · MIT licence</div></section>''' % len(FORMS)
parts = [cover, '<section id="contents"><div class="eyebrow">Contents<span>brief2mp4</span></div><h1>Contents</h1><div class="toc">%s</div>%s</section>' % (toc, note(
    'How to use this guide', 'Read the three rules first. Then find the look you want; each takes half a page. The last pages list the tools by name and say what was and was not verified.'))]
for sid, title, eyebrow, body, _ in SECTIONS:
    head = '<h1>%s</h1>' % E(title) if not sid.startswith('form-') or body.startswith('<p class="lead">') else ''
    parts.append('<section id="%s"><div class="eyebrow">%s<span>brief2mp4 art forms</span></div>%s%s</section>' % (sid, E(eyebrow), head, body))
doc = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>brief2mp4: the art forms guide</title>
<meta name="author" content="Varun Pratap Bhardwaj"><meta name="description" content="%d art forms for animated video, with the rules, timing and build recipe for each.">
<meta name="keywords" content="animation styles, claymation, paper cut-out, cel shading, stop motion, HyperFrames, three.js, Claude Code skill">
<link rel="stylesheet" href="guide.css"></head><body>%s</body></html>''' % (len(FORMS), ''.join(parts))
(HERE / 'brief2mp4-art-forms.html').write_text(doc, encoding='utf-8')
text = re.sub(r'<pre>.*?</pre>', ' ', doc, flags=re.S)
text = re.sub(r'<p class="src">.*?</p>', ' ', text, flags=re.S)
text = re.sub(r'</(p|h1|h2|h3|li|td|th|figcaption|div|a|section)>', '\n', text)
text = html.unescape(re.sub(r'<[^>]+>', '', text))
(HERE / 'guide-prose.txt').write_text('\n'.join(line.strip(, encoding='utf-8') for line in text.splitlines() if line.strip()) + '\n')
print('%d sections, %d words of prose' % (len(SECTIONS) + 2, len(text.split())))
