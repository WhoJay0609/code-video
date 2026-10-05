#!/usr/bin/env python3
"""Capture a local code-video HTML page as stage snapshots and/or WebM."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import tempfile
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote


class CaptureError(RuntimeError):
    pass


def positive_timeout(value: str) -> float:
    try:
        seconds = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timeout must be a number between 1 and 600 seconds") from exc
    if not math.isfinite(seconds) or not 1 <= seconds <= 600:
        raise argparse.ArgumentTypeError("timeout must be a number between 1 and 600 seconds")
    return seconds


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a positive integer") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return number


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture a local deterministic HTML animation as stage PNGs and/or a playable WebM."
    )
    parser.add_argument("html", type=Path, help="local HTML file to open")
    parser.add_argument("--output", type=Path, help="write a playable WebM to this new path")
    parser.add_argument("--snapshots", type=Path, help="write sampled stage PNGs into this directory")
    parser.add_argument("--times", help="comma-separated snapshot seconds; accepts numeric values, half, and end")
    parser.add_argument("--frames", type=Path, help="write an exact PNG frame sequence into this directory")
    parser.add_argument(
        "--max-frames", type=positive_int, default=1800,
        help="refuse frame exports larger than this count (default: 1800; raise explicitly for longer exports)",
    )
    parser.add_argument("--browser", type=Path, help="Chromium executable path; default uses Playwright's browser")
    parser.add_argument(
        "--timeout", type=positive_timeout, default=90,
        help="maximum seconds for page readiness and recording (default: 90; range: 1-600)",
    )
    args = parser.parse_args(argv)
    if args.output is None and args.snapshots is None and args.frames is None:
        parser.error("provide at least one of --output, --snapshots, or --frames")
    if args.times is not None and args.snapshots is None:
        parser.error("--times requires --snapshots")
    if args.output is not None and args.output.suffix.lower() != ".webm":
        parser.error("--output path must end in .webm")
    return args


def local_server(directory: Path) -> tuple[ThreadingHTTPServer, threading.Thread]:
    root = directory.resolve()

    class LocalOnlyHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

        def translate_path(self, path: str) -> str:
            translated = Path(super().translate_path(path)).resolve()
            try:
                translated.relative_to(root)
            except ValueError:
                return str(root / ".__blocked_outside_parent__")
            return str(translated)

        def log_message(self, _format: str, *_args) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), LocalOnlyHandler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, name="code-video-http", daemon=True)
    thread.start()
    return server, thread


def capture_css(width: int, height: int) -> str:
    return f"""
      html, body {{ width: {width}px !important; height: {height}px !important;
        min-width: 0 !important; min-height: 0 !important; margin: 0 !important;
        padding: 0 !important; overflow: hidden !important; }}
      body {{ background: #090e10 !important; }}
      [data-video-stage] {{ position: fixed !important; inset: 0 auto auto 0 !important;
        z-index: 2147483647 !important; width: {width}px !important; height: {height}px !important;
        min-width: 0 !important; max-width: none !important; aspect-ratio: auto !important;
        margin: 0 !important; border: 0 !important; border-radius: 0 !important;
        box-shadow: none !important; transform: none !important; }}
      [data-video-controls] {{ display: none !important; visibility: hidden !important; }}
    """


def fail_on_page_errors(errors: list[str]) -> None:
    if errors:
        first = "\n  ".join(errors[:8])
        extra = "" if len(errors) <= 8 else f"\n  … and {len(errors) - 8} more"
        raise CaptureError(f"browser reported JavaScript/console errors:\n  {first}{extra}")


def attach_error_listeners(page, errors: list[str]) -> None:
    page.on("pageerror", lambda error: errors.append(f"pageerror: {error}"))
    page.on(
        "console",
        lambda message: errors.append(f"console.error: {message.text}") if message.type == "error" else None,
    )


def await_operation(page, operation: str, value, timeout_ms: int):
    """Await ready/seek with a browser-side deadline (evaluate has no timeout kwarg)."""
    return page.evaluate(
        """async ({operation, value, timeoutMs}) => {
          const video = window.__video;
          if (!video) throw new Error('missing window.__video');
          let work;
          if (operation === 'ready') work = video.ready;
          else if (operation === 'seek') work = video.seek(value);
          else throw new Error(`unsupported bounded operation: ${operation}`);
          let timer;
          const deadline = new Promise((_, reject) => {
            timer = setTimeout(() => reject(new Error(`${operation} timed out after ${timeoutMs}ms`)), timeoutMs);
          });
          try { return await Promise.race([Promise.resolve(work), deadline]); }
          finally { clearTimeout(timer); }
        }""",
        {"operation": operation, "value": value, "timeoutMs": timeout_ms},
    )


def parse_snapshot_times(specification: str | None, duration: float) -> list[float]:
    if specification is None:
        return [0.0, duration / 2, duration]
    tokens = specification.split(",")
    if not tokens or any(not token.strip() for token in tokens):
        raise CaptureError("--times must be a comma-separated list of seconds")
    times: list[float] = []
    for token in tokens:
        value = token.strip().lower()
        if value == "half":
            seconds = duration / 2
        elif value == "end":
            seconds = duration
        else:
            try:
                seconds = float(value)
            except ValueError as exc:
                raise CaptureError(f"invalid snapshot time {token!r}; use seconds, half, or end") from exc
        if not math.isfinite(seconds) or not 0 <= seconds <= duration:
            raise CaptureError(f"snapshot time {token!r} must be finite and within 0..{duration:g} seconds")
        times.append(seconds)
    return times


def frame_times(duration: float, fps: float, max_frames: int) -> list[float]:
    count = math.ceil(duration * fps)
    if count > max_frames:
        raise CaptureError(
            f"frame export needs {count} frames, above --max-frames {max_frames}; raise the cap explicitly"
        )
    return [index / fps for index in range(count)]


def output_directory(directory: Path, label: str) -> None:
    if directory.exists() and not directory.is_dir():
        raise CaptureError(f"{label} path is not a directory: {directory}")
    if not directory.parent.is_dir():
        raise CaptureError(f"{label} parent directory does not exist: {directory.parent}")


def snapshot_paths(directory: Path, count: int) -> list[Path]:
    output_directory(directory, "snapshot")
    paths = [directory / f"snapshot-{index:04d}.png" for index in range(1, count + 1)]
    conflict = next((path for path in paths if path.exists()), None)
    if conflict is not None:
        raise CaptureError(f"refusing to overwrite snapshot: {conflict}")
    return paths


def frame_paths(directory: Path, count: int) -> tuple[list[Path], Path]:
    output_directory(directory, "frame")
    manifest = directory / "frames.json"
    if manifest.exists():
        raise CaptureError(f"refusing to overwrite frame metadata: {manifest}")
    if directory.exists():
        existing = next(
            (path for path in directory.iterdir() if path.is_file() and re.fullmatch(r"\d+\.png", path.name)),
            None,
        )
        if existing is not None:
            raise CaptureError(f"refusing to overwrite or mix with existing frame sequence: {existing}")
    return [directory / f"{index:06d}.png" for index in range(count)], manifest


def save_exclusive(path: Path, contents: bytes) -> None:
    created = False
    try:
        with path.open("xb") as stream:
            created = True
            stream.write(contents)
    except FileExistsError as exc:
        raise CaptureError(f"refusing to overwrite output: {path}") from exc
    except Exception:
        if created:
            path.unlink(missing_ok=True)
        raise


def save_json_exclusive(path: Path, metadata: dict) -> None:
    encoded = (json.dumps(metadata, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    save_exclusive(path, encoded)


def capture_sequence(page, directory: Path, samples: list[tuple[float, Path]], timeout_ms: int) -> list[Path]:
    directory.mkdir(exist_ok=True)
    stage = page.locator("[data-video-stage]")
    written: list[Path] = []
    try:
        for seconds, path in samples:
            await_operation(page, "seek", seconds, timeout_ms)
            # "disabled" fast-forwards finite Web Animations; seek already chose frame.
            image = stage.screenshot(animations="allow", timeout=timeout_ms)
            save_exclusive(path, image)
            written.append(path)
        return written
    except Exception:
        for path in written:
            path.unlink(missing_ok=True)
        raise


def read_metadata(page, timeout_ms: int) -> dict:
    page.set_default_timeout(timeout_ms)
    page.wait_for_function(
        "window.__video && window.__video.ready && document.querySelector('[data-video-stage]')",
        timeout=timeout_ms,
    )
    await_operation(page, "ready", None, timeout_ms)
    metadata = page.evaluate(
        """() => {
          const video = window.__video;
          const stage = document.querySelector('[data-video-stage]');
          if (!video || !stage) throw new Error('missing window.__video or [data-video-stage]');
          return {
            width: video.width, height: video.height, duration: video.duration, fps: video.fps,
            stage: true
          };
        }"""
    )
    for key, lower, upper in (
        ("width", 1, 4096),
        ("height", 1, 4096),
        ("duration", 0.01, 600),
        ("fps", 1, 120),
    ):
        value = metadata.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lower <= value <= upper:
            raise CaptureError(f"invalid window.__video.{key}: {value!r}")
        if key in {"width", "height"}:
            if int(value) != value:
                raise CaptureError(f"window.__video.{key} must be a positive integer: {value!r}")
            metadata[key] = int(value)
    return metadata


def prepare_capture_page(page, metadata: dict, timeout_ms: int) -> None:
    width, height = metadata["width"], metadata["height"]
    page.set_default_timeout(timeout_ms)
    page.set_viewport_size({"width": width, "height": height})
    page.add_style_tag(content=capture_css(width, height))
    page.locator("[data-video-stage]").wait_for(state="visible", timeout=timeout_ms)


def record_webm(browser, html_url: str, metadata: dict, output: Path, timeout_ms: int) -> int:
    if not output.parent.is_dir():
        raise CaptureError(f"WebM output directory does not exist: {output.parent}")
    if output.exists():
        raise CaptureError(f"refusing to overwrite WebM: {output}")

    width, height = metadata["width"], metadata["height"]
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="code_video_capture_") as temp_dir:
        context = browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=1,
            record_video_dir=temp_dir,
            record_video_size={"width": width, "height": height},
        )
        page = context.new_page()
        attach_error_listeners(page, errors)
        video = None
        try:
            page.goto(html_url, wait_until="domcontentloaded", timeout=timeout_ms)
            observed = read_metadata(page, timeout_ms)
            if observed != metadata:
                raise CaptureError("video metadata changed between inspection and recording")
            prepare_capture_page(page, metadata, timeout_ms)
            await_operation(page, "seek", 0, timeout_ms)
            video = page.video
            page.evaluate("() => window.__video.play()")
            page.wait_for_function(
                "window.__video && !window.__video.playing && window.__video.time >= window.__video.duration",
                timeout=timeout_ms,
            )
            fail_on_page_errors(errors)
        finally:
            context.close()

        if video is None:
            raise CaptureError("Playwright did not create a page video recording")
        if output.exists():
            raise CaptureError(f"refusing to overwrite WebM: {output}")
        video.save_as(str(output))

    try:
        with output.open("rb") as stream:
            signature = stream.read(4)
    except OSError as exc:
        raise CaptureError(f"could not read recorded WebM: {exc}") from exc
    if signature != bytes.fromhex("1a45dfa3") or output.stat().st_size == 0:
        raise CaptureError(f"recording is empty or does not have a WebM/EBML header: {output}")
    return output.stat().st_size


def run(args: argparse.Namespace) -> None:
    html_path = args.html.expanduser().resolve(strict=True)
    if not html_path.is_file():
        raise CaptureError(f"HTML path is not a file: {html_path}")
    if args.browser is not None:
        browser_path = args.browser.expanduser().resolve(strict=True)
        if not browser_path.is_file() or not os.access(browser_path, os.X_OK):
            raise CaptureError(f"browser path is not an executable file: {browser_path}")
    else:
        browser_path = None
    if args.output is not None:
        args.output = args.output.expanduser().resolve()
        if args.output.exists():
            raise CaptureError(f"refusing to overwrite WebM: {args.output}")
        if not args.output.parent.is_dir():
            raise CaptureError(f"WebM output directory does not exist: {args.output.parent}")
    if args.snapshots is not None:
        args.snapshots = args.snapshots.expanduser().resolve()
    if args.frames is not None:
        args.frames = args.frames.expanduser().resolve()

    server, thread = local_server(html_path.parent)
    port = server.server_address[1]
    html_url = f"http://127.0.0.1:{port}/{quote(html_path.name)}?autoplay=0"
    browser = None
    context = None
    try:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise CaptureError("Playwright Python package is unavailable; install it in this environment first") from exc

        with sync_playwright() as playwright:
            try:
                launch_options = {"headless": True}
                if browser_path is not None:
                    launch_options["executable_path"] = str(browser_path)
                browser = playwright.chromium.launch(**launch_options)
            except Exception as exc:
                detail = str(exc).splitlines()[0]
                hint = " Pass --browser PATH to select an installed Chromium executable." if browser_path is None else ""
                raise CaptureError(f"could not launch Chromium: {detail}.{hint}") from exc

            context = browser.new_context(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
            page = context.new_page()
            errors: list[str] = []
            attach_error_listeners(page, errors)
            try:
                page.goto(html_url, wait_until="domcontentloaded", timeout=int(args.timeout * 1000))
                metadata = read_metadata(page, int(args.timeout * 1000))
                prepare_capture_page(page, metadata, int(args.timeout * 1000))
                if args.snapshots is not None:
                    times = parse_snapshot_times(args.times, metadata["duration"])
                    planned_snapshots = snapshot_paths(args.snapshots, len(times))
                else:
                    times = []
                    planned_snapshots = []
                if args.frames is not None:
                    planned_frame_times = frame_times(
                        metadata["duration"], metadata["fps"], args.max_frames
                    )
                    planned_frames, frame_manifest = frame_paths(args.frames, len(planned_frame_times))
                else:
                    planned_frame_times = []
                    planned_frames = []
                    frame_manifest = None

                if args.snapshots is not None:
                    snapshots = capture_sequence(
                        page,
                        args.snapshots,
                        list(zip(times, planned_snapshots)),
                        int(args.timeout * 1000),
                    )
                else:
                    snapshots = []
                if args.frames is not None:
                    frames = capture_sequence(
                        page,
                        args.frames,
                        list(zip(planned_frame_times, planned_frames)),
                        int(args.timeout * 1000),
                    )
                    manifest_data = {
                        "width": metadata["width"],
                        "height": metadata["height"],
                        "duration": metadata["duration"],
                        "fps": metadata["fps"],
                        "frame_count": len(planned_frame_times),
                        "start_number": 0,
                        "pattern": "%06d.png",
                        "last_frame_time": planned_frame_times[-1],
                    }
                    try:
                        save_json_exclusive(frame_manifest, manifest_data)
                    except Exception:
                        for path in frames:
                            path.unlink(missing_ok=True)
                        raise
                else:
                    frames = []
                fail_on_page_errors(errors)
                context.close()
                context = None

                size = None
                if args.output is not None:
                    started = time.monotonic()
                    size = record_webm(
                        browser, html_url, metadata, args.output, int(args.timeout * 1000)
                    )
                    elapsed = time.monotonic() - started

                print(
                    f"Ready: {metadata['width']}x{metadata['height']}, "
                    f"{metadata['duration']:.2f}s, {metadata['fps']} fps"
                )
                for seconds, path in zip(times, snapshots):
                    print(f"Snapshot t={seconds:g}s: {path}")
                if args.frames is not None:
                    print(
                        f"Frames: {args.frames} ({len(frames)} PNGs, {metadata['fps']} fps, "
                        f"manifest {frame_manifest})"
                    )
                if args.output is not None:
                    print(f"WebM: {args.output} ({size} bytes; capture wall time {elapsed:.1f}s)")
            except CaptureError:
                raise
            except Exception as exc:
                raise CaptureError(f"capture failed: {type(exc).__name__}: {exc}") from exc
    finally:
        if context is not None:
            try:
                context.close()
            except Exception:
                pass
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        run(args)
    except (CaptureError, OSError) as exc:
        print(f"capture_video.py: error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
