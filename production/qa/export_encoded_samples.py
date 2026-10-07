"""Export named diagnostic frames from an existing encoded comparison preview."""

import argparse
from pathlib import Path

import cv2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--frames", type=int, nargs="+", required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(args.video))
    if not capture.isOpened():
        raise RuntimeError(f"Cannot decode {args.video}")
    try:
        for frame in args.frames:
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = capture.read()
            if not ok:
                raise RuntimeError(f"Cannot decode frame {frame}")
            target = args.output / f"f{frame:04d}.jpg"
            if not cv2.imwrite(str(target), image, [cv2.IMWRITE_JPEG_QUALITY, 95]):
                raise RuntimeError(f"Cannot save {target}")
            print(target)
    finally:
        capture.release()


if __name__ == "__main__":
    main()
