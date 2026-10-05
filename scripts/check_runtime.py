#!/usr/bin/env python3
"""Exercise the browser contract and capture tools for a code-video example."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

from capture_video import (
    CaptureError,
    attach_error_listeners,
    await_operation,
    frame_times,
    local_server,
    parse_snapshot_times,
    prepare_capture_page,
    read_metadata,
)


DEFAULT_HTML = Path(__file__).resolve().parents[1] / "assets" / "starter.html"


def timeout_value(value: str) -> float:
    try:
        seconds = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timeout must be between 5 and 600 seconds") from exc
    if not math.isfinite(seconds) or not 5 <= seconds <= 600:
        raise argparse.ArgumentTypeError("timeout must be between 5 and 600 seconds")
    return seconds


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check the code-video browser contract, controls, deterministic seek, and local capture."
    )
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--html", type=Path, help="local HTML file (default: bundled starter)")
    target.add_argument("--url", help="hosted HTTP(S) page to validate in a browser")
    parser.add_argument("--browser", type=Path, help="Chromium executable path")
    parser.add_argument("--timeout", type=timeout_value, default=90,
                        help="bounded wait budget in seconds (default: 90; range: 5-600)")
    parser.add_argument("--artifacts", type=Path,
                        help="directory for check outputs (default: a unique directory under the system temp dir)")
    return parser.parse_args(argv)


def hosted_url(value: str) -> str:
    try:
        parts = urlsplit(value)
    except ValueError as exc:
        raise CaptureError("--url must be a valid absolute HTTP(S) URL") from exc
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise CaptureError("--url must be an absolute HTTP(S) URL")
    query = [(key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True) if key != "autoplay"]
    query.append(("autoplay", "0"))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def unique_artifact_dir(root: Path | None) -> Path:
    parent = (root or Path(tempfile.gettempdir()) / "code-video-check").expanduser().resolve()
    parent.mkdir(parents=True, exist_ok=True)
    candidate = parent / f"run-{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"
    candidate.mkdir(exist_ok=False)
    return candidate


def ensure_controls(page, metadata: dict, timeout_ms: int) -> None:
    for selector in ("[data-play]", "[data-restart]", "#timeline", "[data-readout]"):
        page.locator(selector).wait_for(state="visible", timeout=timeout_ms)
    slider = page.locator("#timeline")
    values = slider.evaluate("element => ({min: Number(element.min), max: Number(element.max), value: Number(element.value)})")
    expected_ms = round(metadata["duration"] * 1000)
    if values["min"] != 0 or abs(values["max"] - expected_ms) > 1:
        raise CaptureError(
            f"#timeline must use a 0..duration*1000 millisecond range; got {values} for {metadata['duration']}s"
        )
    if not math.isfinite(values["value"]):
        raise CaptureError(f"#timeline has an invalid current value: {values['value']!r}")


def wait_seek(page, seconds: float, timeout_ms: int) -> None:
    await_operation(page, "seek", seconds, timeout_ms)
    page.wait_for_function(
        "expected => Math.abs(window.__video.time - expected) < 0.002",
        arg=seconds,
        timeout=timeout_ms,
    )


def check_browser_contract(page, metadata: dict, timeout_ms: int, artifacts: Path) -> None:
    ensure_controls(page, metadata, timeout_ms)
    duration = metadata["duration"]
    readout = page.locator("[data-readout]")
    initial_readout = readout.inner_text()

    # A -> B -> A must render the exact same pixels, even with browser animations present.
    first_time = duration * 0.371
    other_time = duration * 0.813
    wait_seek(page, first_time, timeout_ms)
    stage = page.locator("[data-video-stage]")
    first_image = stage.screenshot(animations="allow", timeout=timeout_ms)
    wait_seek(page, other_time, timeout_ms)
    wait_seek(page, first_time, timeout_ms)
    repeated_image = stage.screenshot(animations="allow", timeout=timeout_ms)
    if first_image != repeated_image:
        raise CaptureError("same-time stage screenshots differ after seek(a) -> seek(b) -> seek(a)")
    (artifacts / "determinism.png").write_bytes(first_image)

    # Exercise the published millisecond range input and its readout.
    slider = page.locator("#timeline")
    target_time = duration * 0.623
    slider.evaluate(
        "(element, value) => { element.value = String(value); element.dispatchEvent(new Event('input', {bubbles: true})); }",
        round(target_time * 1000),
    )
    page.wait_for_function(
        "expected => Math.abs(window.__video.time - expected) < 0.002",
        arg=target_time,
        timeout=timeout_ms,
    )
    if readout.inner_text() == initial_readout:
        raise CaptureError("[data-readout] did not update after moving #timeline")

    # Play, pause, and confirm time no longer advances while paused.
    play_button = page.locator("[data-play]")
    play_button.click()
    page.wait_for_function("window.__video.playing === true", timeout=timeout_ms)
    time.sleep(min(0.12, max(0.02, duration / 20)))
    page.wait_for_function("window.__video.time > 0", timeout=timeout_ms)
    play_button.click()
    page.wait_for_function("window.__video.playing === false", timeout=timeout_ms)
    paused_time = page.evaluate("window.__video.time")
    time.sleep(0.08)
    stable_time = page.evaluate("window.__video.time")
    if abs(stable_time - paused_time) > 0.002:
        raise CaptureError("video time continued to advance after pausing")

    # End positioning and the visible restart control must return to the opening state.
    wait_seek(page, duration, timeout_ms)
    page.locator("[data-restart]").click()
    page.wait_for_function(
        "duration => window.__video.playing === true && window.__video.time < Math.min(0.25, duration * 0.1)",
        arg=duration,
        timeout=timeout_ms,
    )
    play_button.click()
    page.wait_for_function("window.__video.playing === false", timeout=timeout_ms)

    # Full playback has a duration-derived bound, limited by the user's timeout.
    wait_seek(page, 0, timeout_ms)
    play_button.click()
    playback_ms = int(min(timeout_ms / 1000, duration + 5) * 1000)
    page.wait_for_function(
        "window.__video && !window.__video.playing && window.__video.time >= window.__video.duration",
        timeout=max(1000, playback_ms),
    )
    if page.evaluate("window.__video.time") < duration:
        raise CaptureError("full playback stopped before the declared end time")


def fail_page_errors(errors: list[str]) -> None:
    if errors:
        raise CaptureError("browser reported JavaScript/console errors:\n  " + "\n  ".join(errors[:8]))


def waapi_fixture() -> str:
    return """<!doctype html><meta charset="utf-8"><link rel="icon" href="data:,"><title>WAAPI capture fixture</title>
<style>html,body{margin:0;background:#111} [data-video-stage]{position:relative;width:320px;height:180px;overflow:hidden;background:#fff}
#box{position:absolute;left:0;top:60px;width:24px;height:24px;background:#e34b4b}</style>
<section data-video-stage><div id="box"></div></section>
<script>
const box=document.querySelector('#box');
const motion=box.animate([{transform:'translateX(0px)'},{transform:'translateX(120px)'}],
  {duration:1000,fill:'both',easing:'linear'});
motion.pause(); motion.currentTime=0;
let time=0,playing=false;
const ready=Promise.resolve();
async function seek(seconds){playing=false; time=Math.max(0,Math.min(1,Number(seconds))); motion.currentTime=time*1000;
  await new Promise(resolve=>requestAnimationFrame(()=>resolve()));}
window.__video={width:320,height:180,duration:1,fps:4,ready,seek,play(){playing=true;},pause(){playing=false;},get time(){return time;},get playing(){return playing;}};
</script>"""


def run_capture_helper(
    html: Path, args: list[str], timeout: float, browser_path: Path | None
) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(Path(__file__).with_name("capture_video.py")), str(html),
               "--timeout", str(timeout)]
    if browser_path is not None:
        command += ["--browser", str(browser_path)]
    command += args
    return subprocess.run(command, text=True, capture_output=True, timeout=timeout + 15)


def check_capture_features(browser_path: Path | None, timeout: float, artifacts: Path) -> None:
    if parse_snapshot_times(None, 1) != [0.0, 0.5, 1.0]:
        raise CaptureError("default --times samples must be 0, half, and end")
    if parse_snapshot_times("0.25,half,end", 1) != [0.25, 0.5, 1.0]:
        raise CaptureError("numeric and named --times values were not parsed as expected")
    try:
        parse_snapshot_times("1.01", 1)
    except CaptureError:
        pass
    else:
        raise CaptureError("out-of-range --times value was not rejected")

    fixture = artifacts / "waapi-fixture.html"
    fixture.write_text(waapi_fixture(), encoding="utf-8")
    ready_fixture = artifacts / "unresolved-ready.html"
    ready_fixture.write_text(
        waapi_fixture().replace("const ready=Promise.resolve();", "const ready=new Promise(()=>{});"),
        encoding="utf-8",
    )
    snapshots = artifacts / "waapi-snapshots"
    frames = artifacts / "exact-frames"

    ready_output = artifacts / "unresolved-ready-output"
    ready_result = run_capture_helper(
        ready_fixture, ["--snapshots", str(ready_output), "--times", "0"], 1, browser_path
    )
    ready_text = ready_result.stdout + ready_result.stderr
    if ready_result.returncode == 0 or ready_output.exists() or "ready timed out after 1000ms" not in ready_text:
        raise CaptureError(
            "unresolved window.__video.ready did not fail within the configured bounded wait:\n" + ready_text
        )

    snapshot_result = run_capture_helper(
        fixture,
        ["--snapshots", str(snapshots), "--times", "0.25,0.5,end"],
        timeout,
        browser_path,
    )
    if snapshot_result.returncode:
        raise CaptureError(f"WAAPI snapshot capture failed:\n{snapshot_result.stdout}{snapshot_result.stderr}")
    shot_files = sorted(snapshots.glob("snapshot-*.png"))
    if len(shot_files) != 3 or any(path.stat().st_size < 100 for path in shot_files):
        raise CaptureError(f"expected three nonempty sampled PNGs; found {shot_files}")

    # Compare the CLI's middle frame with the same paused WAAPI state in a direct browser page.
    from playwright.sync_api import sync_playwright

    server, thread = local_server(artifacts)
    url = f"http://127.0.0.1:{server.server_address[1]}/{fixture.name}?autoplay=0"
    try:
        with sync_playwright() as playwright:
            launch = {"headless": True}
            if browser_path is not None:
                launch["executable_path"] = str(browser_path)
            browser = playwright.chromium.launch(**launch)
            try:
                page = browser.new_page(viewport={"width": 320, "height": 180}, device_scale_factor=1)
                errors: list[str] = []
                attach_error_listeners(page, errors)
                page.goto(url, wait_until="domcontentloaded", timeout=int(timeout * 1000))
                metadata = read_metadata(page, int(timeout * 1000))
                prepare_capture_page(page, metadata, int(timeout * 1000))
                wait_seek(page, 0.5, int(timeout * 1000))
                stage = page.locator("[data-video-stage]")
                midpoint_allow = stage.screenshot(animations="allow")
                before = page.locator("#box").evaluate("element => getComputedStyle(element).transform")
                if "60" not in before:
                    raise CaptureError(f"WAAPI midpoint is not at 60px before screenshot: {before}")
                if shot_files[1].read_bytes() != midpoint_allow:
                    raise CaptureError("capture helper snapshot did not preserve the requested WAAPI midpoint")
                midpoint_disabled = stage.screenshot(animations="disabled")
                if midpoint_allow == midpoint_disabled:
                    raise CaptureError("WAAPI fixture did not expose Playwright's animation-disabling fast-forward")
                fail_page_errors(errors)
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    # Exact samples are i/fps for i in [0, ceil(duration*fps)); do not append t=duration.
    frame_result = run_capture_helper(
        fixture,
        ["--frames", str(frames), "--max-frames", "4"],
        timeout,
        browser_path,
    )
    if frame_result.returncode:
        raise CaptureError(f"frame export failed:\n{frame_result.stdout}{frame_result.stderr}")
    frame_files = sorted(frames.glob("[0-9][0-9][0-9][0-9][0-9][0-9].png"))
    manifest = json.loads((frames / "frames.json").read_text(encoding="utf-8"))
    expected_times = frame_times(1, 4, 4)
    if len(frame_files) != 4 or [path.name for path in frame_files] != [f"{i:06d}.png" for i in range(4)]:
        raise CaptureError(f"expected exactly four zero-based PNG frames; found {[p.name for p in frame_files]}")
    if (manifest.get("frame_count") != 4 or manifest.get("fps") != 4 or
            manifest.get("pattern") != "%06d.png" or manifest.get("last_frame_time") != expected_times[-1]):
        raise CaptureError(f"unexpected frame metadata: {manifest}")
    if (frames / "000003.png").read_bytes() == shot_files[2].read_bytes():
        raise CaptureError("last sequence frame duplicated the t=duration endpoint")

    # The cap and finite time validation must fail before creating their outputs.
    capped = artifacts / "capped-frames"
    capped_result = run_capture_helper(
        fixture, ["--frames", str(capped), "--max-frames", "3"], timeout, browser_path
    )
    if capped_result.returncode == 0 or capped.exists():
        raise CaptureError("--max-frames did not reject an oversized export before creating output")
    invalid = artifacts / "invalid-times"
    invalid_result = run_capture_helper(
        fixture, ["--snapshots", str(invalid), "--times", "0,nan"], timeout, browser_path
    )
    if invalid_result.returncode == 0 or invalid.exists():
        raise CaptureError("non-finite --times value was not rejected before creating output")

    # Explicitly refuse a repeat export and preserve the existing bytes.
    before_hash = hashlib.sha256((frames / "000000.png").read_bytes()).hexdigest()
    overwrite = run_capture_helper(fixture, ["--frames", str(frames), "--max-frames", "4"], timeout, browser_path)
    after_hash = hashlib.sha256((frames / "000000.png").read_bytes()).hexdigest()
    if overwrite.returncode == 0 or before_hash != after_hash:
        raise CaptureError("repeat frame export did not refuse overwrite without changing existing output")


def check_capture_layout(browser_path: Path | None, timeout_ms: int, artifacts: Path) -> None:
    html = artifacts / "layout-fixture.html"
    html.write_text("""<!doctype html><style>body{margin:0}.shell{width:80vw;margin:20px auto}
      [data-video-stage]{width:640px;height:360px;background:#193;overflow:hidden}
      .controls{display:block;position:fixed;left:0;bottom:0;width:120px;height:30px;background:#f00}
      </style><div class="shell"><section data-video-stage><svg width="24" height="24"></svg></section></div>
      <div class="controls">author controls</div><div data-video-controls>capture controls</div>
      <script>window.__video={width:640,height:360,duration:1,fps:30,ready:Promise.resolve(),time:0,
      async seek(t){this.time=t},play(){},pause(){}};</script>""", encoding="utf-8")
    server, thread = local_server(artifacts)
    url = f"http://127.0.0.1:{server.server_address[1]}/{html.name}?autoplay=0"
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            launch = {"headless": True}
            if browser_path is not None:
                launch["executable_path"] = str(browser_path)
            browser = playwright.chromium.launch(**launch)
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                metadata = read_metadata(page, timeout_ms)
                prepare_capture_page(page, metadata, timeout_ms)
                stage = page.locator("[data-video-stage]").bounding_box()
                nested_svg = page.locator("svg").bounding_box()
                author_controls = page.locator(".controls").evaluate(
                    "element => getComputedStyle(element).display !== 'none' && element.getBoundingClientRect().width > 0"
                )
                hidden_capture_controls = page.locator("[data-video-controls]").evaluate(
                    "element => getComputedStyle(element).display === 'none'"
                )
                if (not stage or stage["width"] != 640 or stage["height"] != 360 or not nested_svg or
                        nested_svg["width"] != 24 or nested_svg["height"] != 24 or
                        not author_controls or not hidden_capture_controls):
                    raise CaptureError("capture layout CSS changed nested scene sizing or hid unrelated author controls")
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def check_webm_playback(path: Path, browser_path: Path | None, timeout_ms: int) -> float:
    from playwright.sync_api import sync_playwright

    if not path.is_file() or path.stat().st_size < 1000:
        raise CaptureError(f"recorded WebM is missing or unexpectedly small: {path}")
    server, thread = local_server(path.parent)
    player_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".html", prefix=".code-video-player-",
            dir=path.parent, delete=False,
        ) as player_file:
            player_file.write(
                '<!doctype html><meta charset="utf-8"><video id="v" controls '
                f'src="{quote(path.name)}"></video>'
            )
            player_path = Path(player_file.name)
        player_url = f"http://127.0.0.1:{server.server_address[1]}/{quote(player_path.name)}"
        with sync_playwright() as playwright:
            launch = {"headless": True}
            if browser_path is not None:
                launch["executable_path"] = str(browser_path)
            browser = playwright.chromium.launch(**launch)
            try:
                page = browser.new_page(viewport={"width": 960, "height": 540})
                page.goto(player_url, wait_until="domcontentloaded", timeout=timeout_ms)
                video = page.locator("#v")
                page.wait_for_function(
                    "() => { const v=document.querySelector('#v'); return v.readyState >= 2 || v.error !== null; }",
                    timeout=timeout_ms,
                )
                media_error = video.evaluate("element => element.error && element.error.message")
                if media_error:
                    raise CaptureError(f"browser could not load recorded WebM: {media_error}")
                duration = video.evaluate("element => element.duration")
                if not math.isfinite(duration) or duration <= 0:
                    raise CaptureError(f"recorded WebM reports invalid duration: {duration!r}")
                video.evaluate("element => element.play()")
                page.wait_for_function("document.querySelector('#v').ended", timeout=timeout_ms)
                if video.evaluate("element => element.error !== null"):
                    raise CaptureError("browser reported a media error while playing the WebM")
                return duration
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        if player_path is not None:
            player_path.unlink(missing_ok=True)


def run(args: argparse.Namespace) -> Path:
    source = args.html or DEFAULT_HTML
    if args.url is not None:
        target = hosted_url(args.url)
        source_path = None
    else:
        source_path = source.expanduser().resolve(strict=True)
        if not source_path.is_file():
            raise CaptureError(f"HTML path is not a file: {source_path}")
        target = None
    browser_path = args.browser.expanduser().resolve(strict=True) if args.browser else None
    if browser_path is not None and (not browser_path.is_file() or not os.access(browser_path, os.X_OK)):
        raise CaptureError(f"browser path is not an executable file: {browser_path}")
    artifacts = unique_artifact_dir(args.artifacts)
    timeout_ms = int(args.timeout * 1000)
    errors: list[str] = []

    server = thread = None
    if source_path is not None:
        server, thread = local_server(source_path.parent)
        target = f"http://127.0.0.1:{server.server_address[1]}/{quote(source_path.name)}?autoplay=0"
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            launch = {"headless": True}
            if browser_path is not None:
                launch["executable_path"] = str(browser_path)
            browser = playwright.chromium.launch(**launch)
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
                attach_error_listeners(page, errors)
                page.goto(target, wait_until="domcontentloaded", timeout=timeout_ms)
                metadata = read_metadata(page, timeout_ms)
                check_browser_contract(page, metadata, timeout_ms, artifacts)
                fail_page_errors(errors)
                print(f"Browser contract: {metadata['width']}x{metadata['height']}, "
                      f"{metadata['duration']:.3f}s, {metadata['fps']} fps; controls, seek, and full playback passed")
            finally:
                browser.close()
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    if source_path is not None:
        check_capture_layout(browser_path, timeout_ms, artifacts)
        check_capture_features(browser_path, args.timeout, artifacts)
        webm = artifacts / "starter.webm"
        command = [sys.executable, str(Path(__file__).with_name("capture_video.py")),
                   str(source_path), "--output", str(webm), "--snapshots", str(artifacts / "starter-keyframes"),
                   "--times", "0,half,end", "--timeout", str(args.timeout)]
        if browser_path is not None:
            command += ["--browser", str(browser_path)]
        captured = subprocess.run(command, text=True, capture_output=True, timeout=args.timeout * 2 + 20)
        if captured.returncode:
            raise CaptureError(f"starter capture failed:\n{captured.stdout}{captured.stderr}")
        played_duration = check_webm_playback(webm, browser_path, timeout_ms)
        if played_duration < metadata["duration"] * 0.9:
            raise CaptureError(f"WebM duration {played_duration:.2f}s is shorter than declared {metadata['duration']:.2f}s")
        print(f"Local capture: snapshots and full WebM playback passed ({played_duration:.2f}s, {webm.stat().st_size} bytes)")
    else:
        print("Hosted URL mode: browser checks passed; local files were not captured")
    print(f"Artifacts: {artifacts}")
    return artifacts


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        run(args)
    except (CaptureError, OSError, subprocess.SubprocessError) as exc:
        print(f"check_runtime.py: error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"check_runtime.py: unexpected {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
