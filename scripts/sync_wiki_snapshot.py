#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import random
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = "https://mewcodex.pages.dev"
USER_AGENT = "nonebot-plugin-mewgenics-wiki-snapshot/1.0"

DATA_FILES = {
    "abilities": "abilities_combined.json",
    "passives": "passives_combined.json",
    "items": "items_db.json",
    "mutations": "mutations_combined.json",
    "characters": "characters_db.json",
}

KIND_FOLDERS = {
    "trinket": "TrinketIcon",
    "weapon": "WeaponIcon",
    "neck": "NeckItemIcon",
    "face": "FaceItemIcon",
    "head": "HeadItemIcon",
}

FONT_ICONS = (
    "str",
    "dex",
    "int",
    "constitution",
    "cha",
    "lck",
    "spd",
    "shield",
    "divineshield",
    "champion",
    "elite",
    "comfort",
    "stimulation",
    "appeal",
    "health",
    "movement",
    "hp",
)


def request(url: str, etag: str | None = None, timeout: float = 30.0):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    if etag:
        req.add_header("If-None-Match", etag)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(), resp.headers.get("ETag")
    except urllib.error.HTTPError as exc:
        if exc.code == 304:
            return 304, b"", etag
        if exc.code == 404:
            return 404, b"", None
        raise


def fetch_bytes(url: str, retries: int = 3) -> bytes:
    for attempt in range(retries):
        try:
            status, body, _ = request(url)
            if status == 200:
                return body
            if status == 404:
                raise FileNotFoundError(url)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt == retries - 1:
                raise
            time.sleep((2**attempt) + random.random())
    raise RuntimeError(f"failed to fetch {url}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def item_icon_path(item: dict) -> str | None:
    frame = item.get("frame")
    if frame is None:
        return None
    folder = KIND_FOLDERS.get(item.get("kind") or "", "TrinketIcon")
    return f"{folder}/{frame}.png"


def item_rarity_path(item: dict) -> str:
    rarity = item.get("rarity")
    cursed = bool(item.get("cursed"))
    consumable = bool(item.get("is_consumable"))

    if rarity in ("quest", "sidequest"):
        return f"rarity/{rarity}{'cursed' if cursed else ''}.png"
    if cursed:
        return "rarity/cursed.png"
    if not rarity:
        return "rarity/unknown.png"
    if rarity == "uncommmon":
        rarity = "uncommon"
    prefix = "consumable_" if consumable else ""
    return f"rarity/{prefix}{rarity}.png"


def collect_assets(data: dict[str, object]) -> set[str]:
    assets: set[str] = set()

    for entry in data["abilities"]:
        frame = entry.get("frame_number")
        if frame is not None:
            assets.add(f"AbilityIcon/{frame}.png")

    for entry in data["passives"]:
        frame = entry.get("frame_number")
        if frame is not None:
            assets.add(f"PassiveIcon/{frame}.png")

    for item in data["items"]:
        icon = item_icon_path(item)
        if icon:
            assets.add(icon)
        assets.add(item_rarity_path(item))
        kind = item.get("kind")
        if kind:
            assets.add(f"parts/{kind}.png")
        if item.get("is_consumable"):
            assets.add("parts/consumable.png")

    for character in data["characters"]:
        image_path = character.get("image_path")
        if image_path:
            assets.add(str(image_path).lstrip("/"))

    for icon in FONT_ICONS:
        assets.add(f"res/fonticon/{icon}.png")

    return assets


def load_manifest(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text("utf-8"))
    except (OSError, ValueError):
        return {}


def sync_data(
    data_dir: Path, old_manifest: dict
) -> tuple[dict[str, object], dict[str, object], bool]:
    data: dict[str, object] = {}
    data_meta: dict[str, object] = {}
    changed = False
    old_etags = old_manifest.get("etags") or {}

    for key, filename in DATA_FILES.items():
        target = data_dir / filename
        etag = old_etags.get(filename)
        status, body, new_etag = request(
            f"{BASE_URL}/{filename}",
            etag if target.exists() else None,
        )
        if status == 304:
            if not target.exists():
                raise RuntimeError(f"304 without local copy: {filename}")
            body = target.read_bytes()
        elif status == 200:
            data_dir.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            if old_etags.get(filename) != new_etag:
                changed = True
        else:
            raise RuntimeError(f"unexpected status {status} for {filename}")

        try:
            parsed = json.loads(body)
        except ValueError as exc:
            raise RuntimeError(f"invalid JSON: {filename}") from exc

        entries = (
            parsed
            if isinstance(parsed, list)
            else parsed.get(key)
            or parsed.get("abilities")
            or parsed.get("passives")
            or parsed.get("mutations")
            or parsed.get("characters")
        )
        if not isinstance(entries, list):
            raise RuntimeError(f"unexpected data shape: {filename}")

        data[key] = entries
        data_meta[filename] = {
            "sha256": hashlib.sha256(body).hexdigest(),
            "size": len(body),
        }
        if new_etag:
            old_etags[filename] = new_etag

    return data, {"files": data_meta, "etags": old_etags}, changed


def sync_assets(
    assets: set[str], asset_dir: Path, workers: int
) -> tuple[list[str], bool]:
    missing: list[str] = []
    changed = False
    pending = [rel for rel in sorted(assets) if not (asset_dir / rel).exists()]

    def download(rel: str) -> tuple[str, bool, bool]:
        url = f"{BASE_URL}/{rel}"
        for attempt in range(3):
            try:
                status, body, _ = request(url)
                if status == 200:
                    target = asset_dir / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(body)
                    return rel, True, False
                if status == 404:
                    return rel, False, True
            except (urllib.error.URLError, TimeoutError, OSError):
                if attempt == 2:
                    return rel, False, False
                time.sleep((2**attempt) + random.random())
        return rel, False, False

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(download, rel) for rel in pending]
        for future in concurrent.futures.as_completed(futures):
            rel, ok, is_missing = future.result()
            if ok:
                changed = True
            elif is_missing:
                missing.append(rel)

    if asset_dir.exists():
        for path in asset_dir.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(asset_dir).as_posix()
            if rel not in assets:
                path.unlink()
                changed = True

    return missing, changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--package",
        type=Path,
        default=Path("nonebot_plugin_mewgenics_wiki"),
    )
    parser.add_argument("--asset-workers", type=int, default=4)
    args = parser.parse_args()

    package = args.package
    data_dir = package / "data"
    asset_dir = package / "assets"
    manifest_path = package / "manifest.json"

    old_manifest = load_manifest(manifest_path)
    data, meta, data_changed = sync_data(data_dir, old_manifest)
    assets = collect_assets(data)
    missing, assets_changed = sync_assets(
        assets, asset_dir, max(1, args.asset_workers)
    )

    if not (data_changed or assets_changed or not manifest_path.exists()):
        print("snapshot is up to date")
        return 0

    now = datetime.now(timezone.utc)
    manifest = {
        "schema_version": 1,
        "snapshot_version": now.strftime("%Y.%m.%d"),
        "generated_at": now.isoformat(timespec="seconds"),
        "source": BASE_URL,
        "counts": {key: len(value) for key, value in data.items()},
        "data": meta["files"],
        "etags": meta["etags"],
        "asset_count": len(assets) - len(missing),
        "missing_assets": sorted(missing),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )

    print(
        f"snapshot updated: {manifest['snapshot_version']}, "
        f"data={sum(manifest['counts'].values())}, "
        f"assets={manifest['asset_count']}, missing={len(missing)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
