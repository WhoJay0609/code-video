# Code Video

A Codex skill for making **playable, editable animations with code**. It takes a brief through visual direction, a seekable timeline, browser checks, and a working presentation of the result.

**[Watch the examples](https://whojay0609.github.io/code-video/)** · [Skill instructions](SKILL.md) · [Library selection](references/library-selection.md) · [Validation](docs/validation.md)

HTML is the default deliverable. WebM recording and deterministic PNG frame export are optional. The built-in examples require no JavaScript packages, remote fonts, model API, or video service.

## What is included

| Component | Entry point | Purpose |
| --- | --- | --- |
| Codex skill | [SKILL.md](SKILL.md) | Choose a visual language and rendering approach for the actual brief. |
| Tool selection | [references/library-selection.md](references/library-selection.md) | Compare browser animation, programmatic video, 2D/3D, audio and encoding tools. |
| Motion direction | [references/motion-direction.md](references/motion-direction.md) | Shape continuity, causal explanation, typography, pixel poses and camera staging. |
| Timeline integration | [references/timeline-adapters.md](references/timeline-adapters.md) | Map a chosen engine to a shared time source without losing its native model. |
| Starter | [assets/starter.html](assets/starter.html) | A self-contained Canvas film with pause, seek and replay. |
| Original examples | [UI Morph](docs/ui-morph.html), [Signal Lab](docs/signal-lab.html) | Two different visual languages; each HTML file includes its editable source. |
| Capture / check tools | [scripts/capture_video.py](scripts/capture_video.py), [scripts/check_runtime.py](scripts/check_runtime.py) | Sample transitions, export frames, record silent WebM and verify playback. |

## Install

Requires Codex with local skill support and Git. Clone into a **new** skill directory:

```bash
git clone https://github.com/WhoJay0609/code-video.git "${CODEX_HOME:-$HOME/.codex}/skills/code-video"
```

If that directory already contains a skill, preserve it and compare changes before replacing it. Start a new Codex task after installation, then ask:

```text
$code-video Create a 20-second visual explanation of how two waves combine.
Use light line art and deliver a playable HTML page.
```

中文也可以直接使用：

```text
$code-video 制作一段 16 秒的 UI 变形短片。使用米白色背景、墨绿色主体，
让同一个按钮依次变成搜索框、进度条和结果卡片，并提供可直接观看的 HTML。
```

The skill name is `code-video`; its display name is **Code Video**. Instructions and detailed references are primarily in Chinese. This is a standalone skill, with no plugin manifest or marketplace registration.

## Try an existing film

Open the [public gallery](https://whojay0609.github.io/code-video/) to play, pause, scrub and restart. To inspect or edit locally, open an example HTML file in your browser. Each is self-contained.

Local playback needs no Python. The optional automation tools need Python 3.10+, Playwright and Chromium:

```bash
cd "${CODEX_HOME:-$HOME/.codex}/skills/code-video"
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
python3 scripts/check_runtime.py
```

These shell commands use the Linux/macOS activation syntax. If a usable Chromium is already installed, pass `--browser /absolute/path/to/chrome` to the scripts instead of downloading another browser. See [validation evidence](docs/validation.md) for the exact environment tested.

Tested first use: the travel-search brief above became the 16-second [UI Morph film](https://whojay0609.github.io/code-video/ui-morph.html). Running the checker with `--html docs/ui-morph.html` and an installed Chromium reported:

```text
Browser contract: 1280x720, 16.000s, 30 fps; controls, seek, and full playback passed
Local capture: snapshots and full WebM playback passed (17.00s, 971075 bytes)
```

## Capture and export

Run from the checkout. Use fresh output paths; existing output files are preserved.

```bash
mkdir -p output

# Inspect specific transitions in the 12-second starter.
python3 scripts/capture_video.py assets/starter.html \
  --snapshots output/keyframes --times 0,3,6,12

# Record actual browser playback. The resulting WebM is silent.
python3 scripts/capture_video.py docs/ui-morph.html \
  --output output/ui-morph.webm

# Export deterministic frames at the film's declared frame rate.
python3 scripts/capture_video.py assets/starter.html --frames output/frames

# Check another film or the public delivery URL.
python3 scripts/check_runtime.py --html docs/signal-lab.html
python3 scripts/check_runtime.py \
  --url https://whojay0609.github.io/code-video/ui-morph.html
```

WebM is real-time playback recording: it may contain startup/end padding and dropped frames, and it does not capture sound. PNG export uses `seek(i / fps)` and `ceil(duration * fps)` frames; a duration off the frame grid rounds up by less than one frame. Use a local FFmpeg build to encode frames or mux an authorized audio track when those outputs are needed. [Runtime and export details](references/browser-runtime.md) include commands and limits.

## Scope and compatibility

- **Tested implementation:** the built-in HTML/Canvas/SVG/Web Animations workflows and Python browser tools. Exact checks and results are recorded in [validation](docs/validation.md).
- **Documented choices:** the third-party libraries in the [selection guide](references/library-selection.md). They are researched options, not bundled dependencies or tested integrations.
- **Unverified:** other agent harnesses, operating systems and browsers unless explicitly listed in the validation record. No cross-harness compatibility claim is made.
- A generated film still needs content and visual review. A passing script does not establish explanatory accuracy, visual quality or access from every client network.
- Paid services, licensed assets and publication require the authorization applicable to that task. The skill itself grants none.

## Develop

Change the relevant instructions, template or script, then run the affected browser check. Preserve the `window.__video` contract described in [browser-runtime.md](references/browser-runtime.md). When changing timing or rendering, verify an arbitrary backward seek and the actual final output.

Report the brief, expected behavior, actual result, browser version and smallest reproduction in an issue. This repository uses GitHub Pages from `main:/docs`; only that directory is served. The public site does not depend on a local preview process.

## Sources and license

[Source notes](references/source-notes.md) identify the original prompt collection and the wider ecosystem research. The examples and skill text are original implementations and summaries. No third-party library code is bundled.

[MIT](LICENSE) covers this repository's original work. Referenced projects and any assets you add retain their own licenses; a project's source being readable does not imply unrestricted reuse.
