"""Compose reviewed character cels over the matching source frame and its text/effects."""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from functools import lru_cache
from pathlib import Path
import subprocess

import cv2
import numpy as np
from PIL import Image, ImageDraw

from opening_clock_layers import restore_clock
from caption_layers import restore_opening_captions
from dance_caption_layers import SOURCE_INTERVAL as DANCE_CAPTION_INTERVAL, NIGHT_INTERVAL as NIGHT_CAPTION_INTERVAL, restore_clear_dance_captions, restore_dance_captions
from raised_caption_layers import SOURCE_INTERVAL as RAISED_CAPTION_INTERVAL, restore_raised_captions
from night_transition_layers import (is_registered as registered_night_transition,
                                     night_subject_mask, restore_night_transition)
from cyan_profile_layers import (is_registered as registered_cyan_profile,
                                 cyan_subject_mask, restore_cyan_profile)
from cyan_caption_layers import restore_cyan_captions
from star_gestures_layers import (is_registered as registered_star_gestures,
                                 star_subject_mask, restore_star_gestures,
                                 restore_star_captions)
from title_layers import compose_registered_title
from star_extended_layers import compose_registered_star_extended
from middle_transition_layers import compose_registered_middle_transition

ROOT = Path(__file__).resolve().parent


def validate_render_timing(timeline, metadata):
    """Reject approximate timing and return this source's exact final exposure length."""
    frames = timeline["frames"]
    start = timeline.get("source_start", 0)
    if (not isinstance(frames, int) or not isinstance(start, int)
            or not 0 <= start < start+frames <= len(metadata["pts"])):
        raise ValueError("Render frame interval must be a nonempty valid source range")
    end = start+frames
    if Path(timeline["source"]).resolve() != Path(metadata["source"]).resolve():
        raise ValueError("Timeline source does not match source timing metadata")
    source_video = next(s for s in metadata["streams"] if s["codec_type"] == "video")
    time_base = Fraction(source_video["time_base"])
    if time_base != Fraction(1, 16000) or timeline.get("fps") != 24:
        raise ValueError("This renderer requires the verified source's 24fps/16000-tick timing")
    if int(source_video["nb_frames"]) != len(metadata["pts"]) or timeline["source_frames"] != len(metadata["pts"]):
        raise ValueError("Source frame count and timing metadata disagree")
    source_pts = [Fraction(str(value)) for value in metadata["pts"]]
    provided_pts = [Fraction(str(value)) for value in timeline.get("source_pts", [])]
    if provided_pts != source_pts[start:end]:
        raise ValueError("Timeline source_pts must exactly match the saved source frame metadata")
    # Millisecond rounding is a property of this source, not a generic CFR assumption.
    quantized_pts = [Fraction((frame * 125 + 1) // 3, 1000) for frame in range(len(source_pts))]
    if source_pts != quantized_pts:
        raise ValueError("Source PTS do not follow the verified millisecond-quantized 24fps pattern")
    boundary = (source_pts[end] if end < len(source_pts)
                else int(source_video["duration_ts"]) * time_base)
    origin = source_pts[start]
    last_duration_ticks = (boundary - source_pts[end - 1]) / time_base
    last_pts_ticks = (source_pts[end - 1]-origin) / time_base
    if last_duration_ticks.denominator != 1 or last_duration_ticks <= 0 or last_pts_ticks.denominator != 1:
        raise ValueError("Final source exposure cannot be represented in the source time base")
    # Test PTS rather than packet index so this also selects the last presentation frame with B-frames.
    bsf = (f"setts=duration=if(eq(PTS\\,{int(last_pts_ticks)})\\,{int(last_duration_ticks)}\\,DURATION)"
           ":time_base=1/16000")
    return {"boundary_seconds": float(boundary-origin), "source_start_seconds": float(origin),
            "source_start_ticks": int(origin/time_base), "last_pts_ticks": int(last_pts_ticks),
            "last_duration_ticks": int(last_duration_ticks), "packet_duration_bsf": bsf}


def source_matches_metadata(source, metadata):
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest() == metadata["sha256"]


def read_image(path):
    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"Cannot decode {path}")
    return cv2.resize(image, (1920, 1080), interpolation=cv2.INTER_LANCZOS4)


def pale_graphics(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    return ((((h >= 17) & (h <= 43) & (s < 43) & (v > 205)) | ((s < 16) & (v > 222))).astype(np.uint8) * 255)


def yellow_graphics(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    return (((h >= 22) & (h <= 38) & (s > 160) & (v > 215)).astype(np.uint8) * 255)


def subject_mask(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    sky = ((h >= 109) & (h <= 145) & (s > 70) & (v > 212)) | ((h >= 84) & (h <= 147) & (s > 160))
    graphics = pale_graphics(image) | yellow_graphics(image)
    seed = ((~sky) & (graphics == 0)).astype(np.uint8)
    connected = cv2.morphologyEx(seed, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(connected, 8)
    selected = np.zeros_like(seed)
    cores_mask = ((h < 22) & (s > 35) & (v > 60)) | ((h >= 80) & (h <= 115) & (s >= 25) & (s < 155) & (v > 85))
    for i in range(1, count):
        x, y, w, height, area = stats[i]
        if area < 1000 or w < 18 or height < 18:
            continue
        region = labels == i
        cores = np.count_nonzero(region & cores_mask)
        if cores > 180:
            selected[labels == i] = 255
    contours, _ = cv2.findContours(selected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(seed)
    cv2.drawContours(filled, contours, -1, 255, cv2.FILLED)
    return cv2.dilate(filled, np.ones((5, 5), np.uint8))


def graphics_mask(image):
    pale = pale_graphics(image)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(pale, 8)
    selected = np.zeros_like(pale)
    for i in range(1, count):
        x, y, w, height, area = stats[i]
        # Pale closed clothing patches are excluded; text strokes and open stars survive.
        density = area / max(1, w * height)
        in_caption_band = y >= 910
        small_left_caption = x + w < 860 and 350 <= y < 840 and w < 90 and height < 55
        if area >= 3 and (in_caption_band or small_left_caption) and ((w < 100 and height < 70) or density < 0.43):
            selected[labels == i] = 255
    yellow = yellow_graphics(image)
    yellow = cv2.dilate(yellow, np.ones((7, 7), np.uint8))
    return selected | yellow


def compose(source, reference, generated, transform=None, asset_source_frame=None, asset_name=None,
            current_frame=None):
    transform = np.float32(transform or [[1, 0, 0], [0, 1, 0]])
    title = compose_registered_title(source, generated, asset_source_frame, asset_name, transform, current_frame)
    if title is not None:
        return title
    extended_star = compose_registered_star_extended(source, generated, current_frame, asset_name, transform)
    if extended_star is not None:
        return extended_star
    middle_transition = compose_registered_middle_transition(source, generated, current_frame, asset_name, transform)
    if middle_transition is not None:
        return middle_transition
    night_transition = registered_night_transition(current_frame, asset_name)
    cyan_profile = registered_cyan_profile(current_frame, asset_name)
    star_gestures = registered_star_gestures(current_frame, asset_name)
    if star_gestures:
        original_subject = star_subject_mask(source, current_frame, asset_name, source=True)
        new_subject = star_subject_mask(generated, current_frame, asset_name)
    elif cyan_profile:
        original_subject = cyan_subject_mask(source, current_frame, asset_name, source=True)
        new_subject = cyan_subject_mask(generated, current_frame, asset_name)
    elif night_transition:
        if 900 <= current_frame < 902:
            original_subject = night_subject_mask(source, current_frame, asset_name,
                                                   existing_mask=subject_mask(source))
            new_subject = night_subject_mask(generated, current_frame, asset_name,
                                              existing_mask=subject_mask(generated))
        else:
            original_subject = night_subject_mask(source, current_frame, asset_name)
            new_subject = night_subject_mask(generated, current_frame, asset_name)
    else:
        original_subject = subject_mask(source)
        new_subject = subject_mask(generated)
    if not np.allclose(transform, [[1, 0, 0], [0, 1, 0]]):
        generated = cv2.warpAffine(generated, transform, (1920, 1080))
        new_subject = cv2.warpAffine(new_subject, transform, (1920, 1080))
    region = original_subject | new_subject
    output = source.copy()
    output[region != 0] = generated[region != 0]
    # Flat exposed source background is known; use it for vacated old hair/coat regions.
    hsv = cv2.cvtColor(generated, cv2.COLOR_BGR2HSV)
    sky = (hsv[:, :, 0] >= 116) & (hsv[:, :, 0] <= 134) & (hsv[:, :, 1] > 70) & (hsv[:, :, 2] > 217)
    shsv = cv2.cvtColor(source, cv2.COLOR_BGR2HSV)
    source_sky = (shsv[:, :, 0] >= 119) & (shsv[:, :, 0] <= 131) & (shsv[:, :, 1] > 70) & (shsv[:, :, 2] > 227)
    samples = source[source_sky]
    if len(samples) > 300000 and np.max(np.std(samples.astype(float), axis=0)) < 8:
        color = np.median(samples, axis=0).astype(np.uint8)
        output[(region != 0) & sky & (new_subject == 0)] = color
    night_repair_mask = np.zeros(source.shape[:2], np.uint8)
    if night_transition:
        output, night_repair_mask = restore_night_transition(output, source, generated,
            original_subject, new_subject, current_frame, asset_name)
    if cyan_profile:
        output, night_repair_mask = restore_cyan_profile(output, source, generated,
            original_subject, new_subject, current_frame, asset_name)
    if star_gestures:
        output, night_repair_mask = restore_star_gestures(output, source, generated,
            original_subject, new_subject, current_frame, asset_name)
    clock_mask = np.zeros(source.shape[:2], np.uint8)
    if current_frame is not None and 0 <= current_frame < 210:
        output, clock_mask = restore_clock(output, source, generated,
                                           asset_source_frame, asset_name, transform)
    overlay = graphics_mask(source)
    if current_frame is not None and 536 <= current_frame < 666:
        # The prone shot has only the right lyric, restored separately below.
        # Its pale sleep-mask highlights are anatomy, not front graphics.
        overlay[:] = 0
    if current_frame is not None and (DANCE_CAPTION_INTERVAL[0] <= current_frame < DANCE_CAPTION_INTERVAL[1]
                                      or NIGHT_CAPTION_INTERVAL[0] <= current_frame < NIGHT_CAPTION_INTERVAL[1]
                                      or RAISED_CAPTION_INTERVAL[0] <= current_frame < RAISED_CAPTION_INTERVAL[1]
                                      or cyan_profile or star_gestures):
        # This source phase has no left lyric; pale candidates include old coat/boot AA.
        # Unedited stars stay source-exact; only registered lyrics and yellow effects go in front.
        overlay = cv2.dilate(yellow_graphics(source), np.ones((7, 7), np.uint8))
    output[overlay != 0] = source[overlay != 0]
    output, caption_mask = restore_opening_captions(output, source, current_frame, asset_name)
    output, clear_caption_mask = restore_clear_dance_captions(output, source, current_frame, asset_name)
    if current_frame is not None and NIGHT_CAPTION_INTERVAL[0] <= current_frame < NIGHT_CAPTION_INTERVAL[1]:
        output, dance_caption_mask = restore_dance_captions(output, source, current_frame, new_subject)
    else:
        output, dance_caption_mask = restore_dance_captions(output, source, current_frame)
    caption_mask |= clear_caption_mask | dance_caption_mask
    if current_frame is not None and RAISED_CAPTION_INTERVAL[0] <= current_frame < RAISED_CAPTION_INTERVAL[1]:
        output, raised_caption_mask = restore_raised_captions(output, source, current_frame, new_subject)
        caption_mask |= raised_caption_mask
    if cyan_profile:
        output, cyan_caption_mask = restore_cyan_captions(output, source, current_frame, new_subject)
        caption_mask |= cyan_caption_mask
    if star_gestures:
        output, star_caption_mask = restore_star_captions(
            output, source, current_frame, asset_name, new_subject)
        caption_mask |= star_caption_mask
    diagnostic = np.concatenate([source, output], axis=1)
    masks = np.zeros_like(source)
    masks[original_subject != 0] = (220, 90, 50)
    masks[new_subject != 0] = (30, 160, 250)
    masks[night_repair_mask != 0] = (180, 100, 220)
    masks[overlay != 0] = (80, 245, 90)
    masks[clock_mask != 0] = (210, 210, 30)
    masks[caption_mask != 0] = (245, 95, 180)
    return output, diagnostic, masks


def main():
    cv2.setNumThreads(2)
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("inspect")
    one.add_argument("source", type=Path)
    one.add_argument("generated", type=Path)
    one.add_argument("--name", required=True)
    one.add_argument("--source-frame", type=int)
    render = sub.add_parser("render")
    render.add_argument("timeline", type=Path)
    render.add_argument("--output", type=Path, required=True)
    render.add_argument("--draft-preview", action="store_true")
    render.add_argument("--side-by-side", action="store_true")
    render.add_argument("--video-encoder", choices=("libx264", "libopenh264"), default="libopenh264")
    args = parser.parse_args()
    if args.command == "inspect":
        source, generated = read_image(args.source), read_image(args.generated)
        output, comparison, masks = compose(source, source, generated,
                                            asset_source_frame=args.source_frame,
                                            asset_name=args.generated.name,
                                            current_frame=args.source_frame)
        target = ROOT / "qa"
        target.mkdir(exist_ok=True)
        cv2.imwrite(str(target / f"{args.name}-composite.png"), output)
        cv2.imwrite(str(target / f"{args.name}-comparison.jpg"), comparison)
        cv2.imwrite(str(target / f"{args.name}-masks.png"), masks)
        print(json.dumps({"comparison":str(target / f"{args.name}-comparison.jpg"),"masks":str(target / f"{args.name}-masks.png")}))
        return
    timeline = json.loads(args.timeline.read_text(encoding="utf-8"))
    if args.draft_preview and not any(word in args.output.stem.lower() for word in ("draft", "preview")):
        raise ValueError("Draft output filename must say draft or preview")
    if not args.draft_preview and any(e.get("review") != "accepted" for e in timeline["output_exposures"]):
        raise ValueError("Render requires accepted output exposures; candidate frames cannot masquerade as a finished PV")
    source = Path(timeline["source"])
    metadata = json.loads((ROOT / "source_meta.json").read_text(encoding="utf-8"))
    timing = validate_render_timing(timeline, metadata)
    if not source_matches_metadata(source, metadata):
        raise ValueError("Source file has changed since frame timing metadata was captured")
    cap = cv2.VideoCapture(str(source))
    start = timeline.get("source_start", 0)
    # Decode forward so a seek/keyframe approximation cannot alter the first cel.
    for frame in range(start):
        if not cap.grab():
            raise ValueError(f"Source ended before requested interval at {frame}")
    width = 3840 if args.side_by_side else 1920
    codec_options = ["-crf", "17", "-preset", "medium"] if args.video_encoder == "libx264" else ["-b:v", "24M" if args.side_by_side else "12M"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    audio_seek = ["-ss", str(timing["source_start_seconds"])] if start else []
    pts_filter = f"settb=1/16000,setpts=round((N+{start})*1000/24)*16-{timing['source_start_ticks']}"
    encoder = subprocess.Popen(["ffmpeg","-y","-v","error","-f","rawvideo","-pixel_format","bgr24","-video_size",f"{width}x1080","-framerate","24","-i","pipe:0",*audio_seek,"-i",str(source),"-map","0:v","-map","1:a:0","-vf",pts_filter,"-fps_mode","passthrough","-enc_time_base","1:16000","-video_track_timescale","16000","-t",str(timing["boundary_seconds"]),"-c:v",args.video_encoder,*codec_options,"-pix_fmt","yuv420p","-bsf:v",timing["packet_duration_bsf"],"-c:a","copy","-movflags","+faststart",str(args.output)],stdin=subprocess.PIPE)
    exposures = timeline["output_exposures"]
    index = 0
    assets = timeline["assets"]
    @lru_cache(maxsize=8)
    def load_cel(cel):
        asset = assets[cel]
        return read_image(args.timeline.parent / asset["source_reference"]), read_image(args.timeline.parent / asset["path"])
    try:
        for frame in range(start, start+timeline["frames"]):
            ok, current = cap.read()
            if not ok:
                raise ValueError(f"Source ended early at frame {frame}")
            while frame >= exposures[index]["end"]:
                index += 1
            exposure = exposures[index]
            reference, generated = load_cel(exposure["cel"])
            asset = assets[exposure["cel"]]
            output, _, _ = compose(current, reference, generated, exposure.get("source_matrix"),
                                   asset["source_frame"], Path(asset["path"]).name, frame)
            if args.side_by_side:
                output = np.concatenate([current, output], axis=1)
            encoder.stdin.write(output.tobytes())
        encoder.stdin.close()
        if encoder.wait() != 0:
            raise RuntimeError("FFmpeg encoding failed")
    finally:
        cap.release()
        if encoder.poll() is None:
            encoder.terminate()


if __name__ == "__main__":
    main()
