"""Prepare or render a compressed source-left/master-right review comparison."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "qa" / "full-draft-one-pass-2026-10-07"
MASTER = ROOT / "output" / "klee-full-oct7-draft-v1.mp4"
OUTPUT = ROOT / "output" / "klee-full-oct7-comparison-draft-v1.mp4"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def timing(metadata):
    video = next(s for s in metadata["streams"] if s["codec_type"] == "video")
    expected = [Fraction((n * 125 + 1) // 3, 1000) for n in range(3658)]
    if ([Fraction(str(p)) for p in metadata["pts"]] != expected
            or video["time_base"] != "1/16000" or int(video["nb_frames"]) != 3658
            or (video["width"], video["height"]) != (1920, 1080)
            or int(video["duration_ts"]) != 2438666):
        raise ValueError("Source metadata must retain the verified complete-PV timing")
    last_pts = int(expected[-1] * 16000)
    last_duration = int(video["duration_ts"]) - last_pts
    if last_duration != 666:
        raise ValueError("Final source presentation duration must be 666 ticks")
    return {"frames": 3658, "time_base": "1/16000", "last_pts_ticks": last_pts,
            "last_duration_ticks": last_duration, "video_seconds": "152.416625"}


def build_command(source, master, output, clock):
    pts = "settb=1/16000,setpts=round(N*1000/24)*16"
    graph = (f"[0:v:0]{pts}[left];[1:v:0]{pts}[right];"
             f"[left][right]hstack=inputs=2:shortest=1,{pts}[video]")
    duration = (f"setts=duration=if(eq(PTS\\,{clock['last_pts_ticks']})\\,"
                f"{clock['last_duration_ticks']}\\,DURATION):time_base=1/16000")
    return ["ffmpeg", "-nostdin", "-n", "-hide_banner", "-v", "warning",
            "-i", str(source), "-i", str(master), "-filter_complex", graph,
            "-map", "[video]", "-map", "0:a:0",
            "-fps_mode", "passthrough", "-enc_time_base", "1:16000",
            "-video_track_timescale", "16000", "-t", clock["video_seconds"],
            "-c:v", "libopenh264", "-b:v", "24M", "-pix_fmt", "yuv420p",
            "-bsf:v", duration, "-c:a", "copy", "-movflags", "+faststart",
            "-metadata", "comment=Compressed review comparison, not the master; source left, draft master right",
            str(output)]


def validate_master(master, clock):
    result = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                             "-show_streams", "-show_frames", "-show_entries",
                             "stream=width,height,time_base,duration_ts:frame=pts",
                             "-of", "json", str(master)], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", check=True)
    if result.stderr.strip():
        raise ValueError(result.stderr.strip())
    info = json.loads(result.stdout)
    stream = info["streams"][0]
    expected = [((n * 125 + 1) // 3) * 16 for n in range(clock["frames"])]
    if ([int(f["pts"]) for f in info["frames"]] != expected
            or stream["time_base"] != clock["time_base"]
            or int(stream["duration_ts"]) != 2438666
            or (stream["width"], stream["height"]) != (1920, 1080)):
        raise ValueError("Encoded main master must have all 3658 exact source PTS and dimensions")


def self_test(metadata):
    clock = timing(metadata)
    assert clock["last_pts_ticks"] == 2438000
    assert clock["last_duration_ticks"] == 666
    assert Fraction(clock["video_seconds"]) == Fraction(2438666, 16000)
    command = build_command(Path("source.mp4"), MASTER, OUTPUT, clock)
    assert command[command.index("-map") + 1] == "[video]"
    assert command[command.index("-c:a") + 1] == "copy"
    assert "hstack=inputs=2:shortest=1" in command[command.index("-filter_complex") + 1]
    assert "\\,666\\," in command[command.index("-bsf:v") + 1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, default=MASTER)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--render", action="store_true", help="Explicitly execute the prepared full render")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    metadata = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    clock = timing(metadata)
    if args.self_test:
        self_test(metadata)
    source, master, output = Path(metadata["source"]), args.master.resolve(), args.output.resolve()
    if source.resolve() == output or master == output or "comparison" not in output.stem or "draft" not in output.stem:
        raise ValueError("Comparison draft output must be distinct from its source and main master")
    command = build_command(source, master, output, clock)
    AUDIT.mkdir(parents=True, exist_ok=True)
    plan = {"snapshot_utc": datetime.now(timezone.utc).isoformat(),
            "kind": "extra-compressed-review-comparison-not-master", "source": str(source),
            "main_master": str(master), "output": str(output), "timing": clock,
            "command": command, "windows_command_line": subprocess.list2cmdline(command),
            "source_audio_copy": True, "aac_priming": "Retain original packets without seeking or timestamp shifts",
            "composition_repeated": False, "artistic_review": "not_performed",
            "status": "prepared_not_rendered", "self_test_passed": args.self_test}
    plan["verification_command"] = ["python", str(ROOT / "verify_preview.py"), str(output),
                                    "--end", str(clock["frames"]), "--side-by-side", "--report",
                                    str(AUDIT / "comparison-technical-verification.json")]
    audit = AUDIT / "comparison-command.json"
    audit.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    if args.render:
        if not master.is_file():
            raise FileNotFoundError("The completed encoded main master is required before comparison render")
        if digest(source) != metadata["sha256"]:
            raise ValueError("Original source identity changed")
        validate_master(master, clock)
        output.parent.mkdir(parents=True, exist_ok=True)
        plan.update(status="rendering", master_sha256=digest(master))
        audit.write_text(json.dumps(plan, indent=2), encoding="utf-8")
        with (AUDIT / "comparison-ffmpeg.log").open("w", encoding="utf-8") as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        plan.update(status="rendered_unverified" if result.returncode == 0 else "render_failed",
                    returncode=result.returncode, master_unchanged=digest(master) == plan["master_sha256"])
        audit.write_text(json.dumps(plan, indent=2), encoding="utf-8")
        if result.returncode:
            raise SystemExit(result.returncode)
    else:
        (AUDIT / "comparison-preparation.log").write_text(
            "Prepared only; FFmpeg was not started. Main master required before --render.\n"
            + plan["windows_command_line"] + "\n", encoding="utf-8")
    print(json.dumps({"audit": str(audit), "status": plan["status"], "self_test_passed": args.self_test}))


if __name__ == "__main__":
    main()
