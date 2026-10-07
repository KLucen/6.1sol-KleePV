"""Build, restore and publish a byte-preserving complete project snapshot."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "archive"
LOCAL = ROOT / "_upload"
REPO = "KLucen/6.1sol-KleePV"
TAG = "engineering-snapshot-2026-10-07"
EXCLUDED_ROOTS = {".git", "_upload", "archive"}
TEXT_SUFFIXES = {".py", ".json", ".md", ".txt", ".csv", ".log"}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def project_paths():
    for directory, folders, names in os.walk(ROOT):
        relative = Path(directory).relative_to(ROOT)
        if relative == Path("."):
            folders[:] = [name for name in folders if name not in EXCLUDED_ROOTS]
        for name in sorted(names):
            path = Path(directory) / name
            if path.is_symlink():
                raise ValueError(f"Snapshot cannot silently follow a symlink: {path}")
            yield path


def build(limit):
    if (META / "project-files.json").exists():
        raise FileExistsError("Snapshot already exists; do not rebuild or overwrite it")
    files, objects, directories, direct = [], {}, set(), []
    for number, path in enumerate(sorted(project_paths()), 1):
        relative = path.relative_to(ROOT).as_posix()
        stat = path.stat()
        sha = digest(path)
        if path.stat().st_mtime_ns != stat.st_mtime_ns:
            raise ValueError(f"File changed while scanning: {relative}")
        files.append({"path": relative, "bytes": stat.st_size, "sha256": sha,
                      "mtime_ns": stat.st_mtime_ns})
        objects.setdefault(sha, {"path": relative, "bytes": stat.st_size})
        for parent in PurePosixPath(relative).parents:
            if str(parent) != ".":
                directories.add(str(parent))
        if (".python_deps" not in path.parts and "__pycache__" not in path.parts
                and (path.suffix.lower() in TEXT_SUFFIXES or path.name in {".gitignore", ".gitattributes"})):
            direct.append(relative)
        if number % 1000 == 0:
            print(f"Hashed {number} files", flush=True)
    for directory, folders, _ in os.walk(ROOT):
        relative = Path(directory).relative_to(ROOT)
        if relative == Path("."):
            folders[:] = [name for name in folders if name not in EXCLUDED_ROOTS]
        else:
            directories.add(relative.as_posix())
    batches, batch, size = [], [], 0
    for sha, obj in sorted(objects.items()):
        if obj["bytes"] > limit:
            raise ValueError(f"Object exceeds volume limit: {obj['path']}")
        if batch and size + obj["bytes"] > limit:
            batches.append(batch)
            batch, size = [], 0
        batch.append(sha)
        size += obj["bytes"]
    if batch:
        batches.append(batch)
    stats = {"files": len(files), "original_bytes": sum(f["bytes"] for f in files),
             "unique_objects": len(objects), "unique_bytes": sum(o["bytes"] for o in objects.values()),
             "volumes": len(batches), "direct_git_files": len(direct)}
    print(json.dumps(stats), flush=True)
    LOCAL.mkdir(exist_ok=True)
    volume_records = []
    object_volume = {}
    for number, batch in enumerate(batches, 1):
        name = f"engineering-objects-{number:02d}-of-{len(batches):02d}.zip"
        archive = LOCAL / name
        with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as zipped:
            for sha in batch:
                obj = objects[sha]
                actual = hashlib.sha256()
                with (ROOT / obj["path"]).open("rb") as source, zipped.open(f"objects/{sha}", "w") as target:
                    while chunk := source.read(1024 * 1024):
                        target.write(chunk)
                        actual.update(chunk)
                if actual.hexdigest() != sha:
                    raise ValueError(f"Source changed while archiving: {obj['path']}")
                object_volume[sha] = name
        if archive.stat().st_size >= 2 * 1024**3:
            raise ValueError("Release volume must be smaller than 2 GiB")
        volume_records.append({"name": name, "bytes": archive.stat().st_size,
                               "sha256": digest(archive), "objects": len(batch)})
        print(f"Built {name}: {archive.stat().st_size} bytes", flush=True)
    for item in files:
        item["volume"] = object_volume[item["sha256"]]
    manifest = {"format": "klee-byte-preserving-snapshot-v1", "snapshot_utc": datetime.now(timezone.utc).isoformat(),
                "source_root": str(ROOT), "statistics": stats, "files": files,
                "directories": sorted(directories), "excluded": [".git internals", "_upload upload staging", "archive generated snapshot metadata"],
                "original_engineering_files_excluded": 0}
    write(META / "project-files.json", manifest)
    write(META / "volumes.json", {"format": manifest["format"], "volumes": volume_records,
                                 "manifest_sha256": digest(META / "project-files.json")})
    direct += ["archive/project-files.json", "archive/volumes.json"]
    (LOCAL / "git-paths.nul").write_bytes(b"".join((":(literal)" + p).encode("utf-8") + b"\0" for p in direct))
    print(json.dumps({"build_complete": True, "statistics": stats,
                      "archive_bytes": sum(v["bytes"] for v in volume_records)}), flush=True)


def safe_path(destination, relative):
    parsed = PurePosixPath(relative)
    if parsed.is_absolute() or any(part in {"..", "."} or ":" in part or "\\" in part for part in parsed.parts):
        raise ValueError(f"Unsafe snapshot path: {relative}")
    result = destination.joinpath(*parsed.parts)
    if not result.resolve().is_relative_to(destination.resolve()):
        raise ValueError(f"Snapshot path escapes destination: {relative}")
    return result


def restore(volumes, destination):
    manifest, index = read(META / "project-files.json"), read(META / "volumes.json")
    if digest(META / "project-files.json") != index["manifest_sha256"]:
        raise ValueError("Manifest SHA-256 mismatch")
    grouped = defaultdict(list)
    for item in manifest["files"]:
        safe_path(destination, item["path"])
        grouped[item["volume"]].append(item)
    destination.mkdir(parents=True, exist_ok=True)
    for directory in manifest["directories"]:
        safe_path(destination, directory).mkdir(parents=True, exist_ok=True)
    for volume in index["volumes"]:
        archive = volumes / volume["name"]
        if archive.stat().st_size != volume["bytes"] or digest(archive) != volume["sha256"]:
            raise ValueError(f"Archive integrity mismatch: {archive.name}")
        with zipfile.ZipFile(archive) as zipped:
            for item in grouped[volume["name"]]:
                target = safe_path(destination, item["path"])
                if target.exists():
                    if target.is_file() and digest(target) == item["sha256"]:
                        continue
                    raise FileExistsError(f"Different existing file, refusing overwrite: {target}")
                temporary = target.with_name(target.name + ".snapshot-restoring")
                actual = hashlib.sha256()
                with zipped.open("objects/" + item["sha256"]) as source, temporary.open("xb") as output:
                    while chunk := source.read(1024 * 1024):
                        output.write(chunk)
                        actual.update(chunk)
                if actual.hexdigest() != item["sha256"] or temporary.stat().st_size != item["bytes"]:
                    raise ValueError(f"Restored file integrity mismatch: {target}")
                temporary.rename(target)
                os.utime(target, ns=(item["mtime_ns"], item["mtime_ns"]))
        print(f"Verified and restored {archive.name}", flush=True)
    print(json.dumps({"restore_complete": True, "files": len(manifest["files"])}), flush=True)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("Authenticated API redirects are not permitted")


class UploadReader:
    def __init__(self, stream, total, name):
        self.stream, self.total, self.name = stream, total, name
        self.sent, self.last = 0, time.monotonic()

    def read(self, size):
        chunk = self.stream.read(max(size, 1024 * 1024))
        self.sent += len(chunk)
        now = time.monotonic()
        if now - self.last >= 20:
            print(f"Sending {self.name}: {self.sent}/{self.total} bytes", flush=True)
            self.last = now
        return chunk


def credential():
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="Never")
    result = subprocess.run(["git", "-c", "credential.interactive=never", "credential", "fill"],
                            input="protocol=https\nhost=github.com\n\n", text=True,
                            capture_output=True, env=env, check=True)
    fields = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    if not fields.get("password"):
        raise ValueError("No stored GitHub credential; authenticate Git first")
    return fields["password"]


def publish(proxy):
    token = credential()
    handlers = [NoRedirect()]
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    opener = urllib.request.build_opener(*handlers)
    headers = {"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2026-03-10", "User-Agent": "KleePV-Engineering-Archive"}

    def api(route, method="GET", payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(f"https://api.github.com/repos/{REPO}/{route}",
                                         data=data, method=method, headers=headers)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        with opener.open(request, timeout=90) as response:
            body = response.read()
        return json.loads(body) if body else None

    manifest, index = read(META / "project-files.json"), read(META / "volumes.json")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if api("git/ref/heads/main")["object"]["sha"] != commit:
        raise ValueError("Remote main does not match the committed snapshot metadata")
    body = ("Complete byte-preserving engineering snapshot. First-draft PV; not artistic acceptance.\n\n"
            f"{len(manifest['files'])} original paths; {manifest['statistics']['unique_objects']} unique byte objects.\n"
            "Download every engineering-objects ZIP and restore with tools/engineering_archive.py.\n"
            "Repository source ZIP alone omits large assets. File paths and SHA-256 are in archive/project-files.json.\n\n"
            "Upload is in progress; complete status requires all remote asset SHA-256 checks.\n")
    try:
        release = api("releases/tags/" + TAG)
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        release = api("releases", "POST", {"tag_name": TAG, "target_commitish": commit,
                      "name": "Complete engineering snapshot - 2026-10-07", "body": body,
                      "draft": False, "prerelease": True})
    expected = [(META / "project-files.json", None), (META / "volumes.json", None),
                (ROOT / "production/output/klee-full-oct7-draft-v1.mp4", None),
                (ROOT / "production/output/klee-full-oct7-comparison-draft-v1.mp4", None)]
    expected += [(LOCAL / v["name"], v["sha256"]) for v in index["volumes"]]
    verified = []
    for path, known_sha in expected:
        sha = digest(path)
        if known_sha is not None and sha != known_sha:
            raise ValueError(f"Local archive changed: {path.name}")
        assets = api(f"releases/{release['id']}/assets?per_page=100")
        asset = next((a for a in assets if a["name"] == path.name), None)
        if asset is None:
            url = f"https://uploads.github.com/repos/{REPO}/releases/{release['id']}/assets?name={urllib.parse.quote(path.name)}"
            with path.open("rb") as stream:
                request = urllib.request.Request(url, method="POST", data=UploadReader(stream, path.stat().st_size, path.name),
                                                 headers={**headers, "Content-Type": "application/octet-stream",
                                                          "Content-Length": str(path.stat().st_size)})
                with opener.open(request, timeout=600) as response:
                    asset = json.loads(response.read())
        if (asset["state"] != "uploaded" or asset["size"] != path.stat().st_size
                or asset.get("digest") != "sha256:" + sha):
            raise ValueError(f"Remote asset not verified; refusing to overwrite: {path.name}")
        verified.append({"name": path.name, "id": asset["id"], "bytes": asset["size"],
                         "sha256": sha, "url": asset["browser_download_url"]})
        write(LOCAL / "publication-progress.json", {"complete": False, "commit": commit,
              "release": release["html_url"], "verified_assets": verified})
        print(f"Remote SHA-256 verified: {path.name}", flush=True)
    final_body = body.replace("Upload is in progress; complete status requires all remote asset SHA-256 checks.",
                              "Upload complete. Every asset size and server-computed SHA-256 matches the local file.")
    api(f"releases/{release['id']}", "PATCH", {"body": final_body})
    result = {"complete": True, "commit": commit, "release": release["html_url"],
              "source_files": len(manifest["files"]), "original_engineering_files_excluded": 0,
              "verified_assets": verified}
    write(LOCAL / "publication-result.json", result)
    print(json.dumps(result), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("build")
    create.add_argument("--volume-bytes", type=int, default=1800 * 1024**2)
    unpack = sub.add_parser("restore")
    unpack.add_argument("--volumes", type=Path, required=True)
    unpack.add_argument("--destination", type=Path, required=True)
    upload = sub.add_parser("publish")
    upload.add_argument("--proxy")
    args = parser.parse_args()
    if args.command == "build":
        build(args.volume_bytes)
    elif args.command == "restore":
        restore(args.volumes.resolve(), args.destination.resolve())
    else:
        publish(args.proxy)


if __name__ == "__main__":
    main()
