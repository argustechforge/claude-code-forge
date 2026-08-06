# Frontier Model Use Efficiency

Lightning Lesson given to the Houston AI Club on 6 August 2026. 30 slides, 30 minutes.

Getting more out of Claude Code and the Codex CLI, and what carries over to Cowork. The talk works
through task difficulty against model tier against effort level, walks the Model Router end to end,
then covers the cheap wins, the multi-provider handoff to Codex, and where the effort dial stops.

The tooling in this repo is what the talk is built on. [`ModelRouter/`](../../ModelRouter/) is the
router demonstrated in the walkthrough, and [`guides/`](../../guides/) covers the reasoning behind
it.

## View it

- **Interactive:** open [`index.html`](index.html) in any browser. Arrow keys move between slides.
- **PDF:** [`Frontier_Model_Use_Efficiency_deck.pdf`](Frontier_Model_Use_Efficiency_deck.pdf),
  30 pages, works offline.
- **Images:** [`slides/`](slides/), one PNG per slide, for quick preview or embedding elsewhere.

## Contents

| | |
|---|---|
| `index.html` | The deck. Self-contained, a 1280x720 stage that scales to the viewport. |
| `assets/` | Six inline SVG diagrams the deck loads locally. |
| `slides/` | 30 PNG exports, `slide_01.png` through `slide_30.png`. |
| `Frontier_Model_Use_Efficiency_deck.pdf` | Print and offline version. |

## Notes

`index.html` makes no network requests. Fonts are local-or-fallback stacks so nothing can hang on
venue wifi mid-talk, and the diagrams load from `assets/` rather than a CDN. It falls back to system
sans and mono stacks when IBM Plex Sans and JetBrains Mono are not installed.

Slide footers carry the segment number and target timestamp from the run sheet. Those are presenter
cues, not part of the content.
