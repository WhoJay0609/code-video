# Validation record

Date: 2026-10-05. These results cover the native examples and browser tools in this repository. They do not establish compatibility with every library in the research guide.

## Environment and commands

Tested on Linux with Python 3.11.7, Playwright 1.62.0, and Google Chrome for Testing 153.0.8010.12. An existing Chromium executable was supplied through `--browser`; the default Playwright browser download was not used. System FFmpeg was not installed. Playwright's recording component produced the WebM files.

From the repository, substitute the absolute path to your installed Chromium:

```bash
python3 scripts/check_runtime.py --html assets/starter.html \
  --browser /absolute/path/to/chrome --artifacts output/check-starter
python3 scripts/check_runtime.py --html docs/ui-morph.html \
  --browser /absolute/path/to/chrome --artifacts output/check-ui
python3 scripts/check_runtime.py --html docs/signal-lab.html \
  --browser /absolute/path/to/chrome --artifacts output/check-signal
```

Each check creates a unique run directory. It saves deterministic-seek images, sampled frames, a numbered PNG fixture with its manifest, and the recorded WebM. The checker names the recording `starter.webm` for every local input; its content comes from the selected `--html` file.

## Observed results

The 12-second Canvas starter passed controls, deterministic seeking, full playback, layout checks, capture regressions and WebM playback. Its recorded file was 935,168 bytes and played to `ended` at 13.00 seconds.

The 16-second UI Morph example produced this output:

```text
Browser contract: 1280x720, 16.000s, 30 fps; controls, seek, and full playback passed
Local capture: snapshots and full WebM playback passed (17.00s, 971075 bytes)
```

The 18-second Signal Lab example also passed the complete local check:

```text
Browser contract: 1280x720, 18.000s, 30 fps; controls, seek, and full playback passed
Local capture: snapshots and full WebM playback passed (19.08s, 1457799 bytes)
```

Recording duration differs from scene duration because this is real-time browser recording, with startup/end padding. The declared 30 fps is the scene's frame-export rate, not a guarantee about this recording's encoded frame rate.

The capture regression uses a paused Web Animations fixture. At 0.5 seconds the moving box must remain at 60 pixels. The capture helper preserved that position; a comparison using Playwright's `animations="disabled"` fast-forwarded it. This reproduces and checks the screenshot defect fixed in this version.

PNG export produced exactly `000000.png` through `000003.png` for a one-second, four-fps fixture. `frames.json` recorded four frames and `last_frame_time: 0.75`; the export did not append the duration endpoint. Tests also covered explicit snapshot times, rejection of non-finite/out-of-range times, frame caps, and refusal to overwrite existing output. An unresolved `ready` promise failed after the configured one-second deadline without creating its output directory.

## Creative briefs and visual review

| Brief | Implementation and inspected behavior |
| --- | --- |
| Transform one travel-search object into a useful result, with cream/green styling and causal cursor actions. | [UI Morph](ui-morph.html), 16 seconds, SVG plus a paused WAAPI shape track. Reviewed opening, search expansion, submit, progress, result reveal, save and final hold. Corrected overlapping transition text and an empty result handoff. |
| Explain how two known sine components form a signal, using light line art and a shared probe. | [Signal Lab](signal-lab.html), 18 seconds, SVG driven by analytic functions. The 1 Hz component has amplitude 1; the 3 Hz component has amplitude 0.5. The sum and probe use the same functions and vertical scale. Spectrum bars preserve the 2:1 amplitude ratio. The page labels the signal as synthetic. Rounded probe values use `≈`. |

Both examples were checked at storyboard boundaries and motion midpoints. Repeated `seek(a) → seek(b) → seek(a)` images matched. Natural playback reached the declared end time. The UI's final sought/playback images matched; Signal Lab's final DOM matched immediately and its images matched after two browser animation frames. Immediate SVG raster captures can differ slightly while the browser compositor settles.

The gallery was inspected at 1440×1100 and 390×844. Both layouts passed the horizontal-overflow check. Example aspect ratios and controls were also checked at a narrow viewport. Detailed scene text is intended for a larger viewing area; a scaled phone preview is not a substitute for readable full-size presentation.

## Research and remaining limits

The [selection guide](../references/library-selection.md), [timeline adapters](../references/timeline-adapters.md) and [source notes](../references/source-notes.md) connect official sources to adopted methods. The research review corrected playback-rate assumptions in the Three.js and Lottie positioning recipes. Third-party integrations remain documentation-only.

No MP4 encoding, audio capture/muxing, GPU rendering, third-party framework installation, other operating system, or non-Chromium browser was tested. The examples are silent and have no external resources. The optional FFmpeg, Tone, WebCodecs and other routes require their own project-specific checks. Browser checks verify mechanics; content correctness and visual quality still require inspection.
