"""Run HACS's file-validation schemas against the local working tree."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from custom_components.hacs.utils.validate import (
    HACS_MANIFEST_JSON_SCHEMA,
    INTEGRATION_MANIFEST_CATEGORIES_SCHEMA,
    INTEGRATION_MANIFEST_JSON_SCHEMA,
)
from voluptuous import Invalid, Schema
from voluptuous.humanize import humanize_error


def load_json(path: Path) -> dict[str, Any]:
    """Load a local JSON object."""
    try:
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, UnicodeError, json.JSONDecodeError) as err:
        raise ValueError(f"{path}: {err}") from err
    if not isinstance(data, dict):
        raise TypeError(f"{path}: expected a JSON object")
    return data


def validate_schema(name: str, data: dict[str, Any], schema: Schema) -> None:
    """Apply an upstream HACS schema."""
    try:
        schema(data)
    except Invalid as err:
        raise ValueError(f"{name}: {humanize_error(data, err)}") from err
    print(f"{name}: passed")


def main(root: Path) -> int:
    """Validate local files; GitHub repository metadata is not checked."""
    try:
        tree = subprocess.run(
            [
                "git", "-C", str(root), "ls-files", "-z",
                "--cached", "--others", "--exclude-standard",
            ],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.split("\0")
        files = {path for path in tree if path and (root / path).is_file()}

        if "hacs.json" not in files:
            raise ValueError("The repository has no tracked or unignored hacs.json")
        hacs = load_json(root / "hacs.json")
        validate_schema("hacs.json", hacs, HACS_MANIFEST_JSON_SCHEMA)
        if hacs.get("zip_release") and not hacs.get("filename"):
            raise ValueError("hacs.json: zip_release is true but filename is not set")

        integration = (
            Path() if hacs.get("content_in_root") else Path("custom_components/wth_umr2")
        )
        manifest_path = integration / "manifest.json"
        if manifest_path.as_posix() not in files:
            raise ValueError(f"The repository has no tracked or unignored {manifest_path}")
        manifest = load_json(root / manifest_path)
        validate_schema(str(manifest_path), manifest, INTEGRATION_MANIFEST_JSON_SCHEMA)
        if "categories" in manifest:
            validate_schema(
                "integration categories", manifest, INTEGRATION_MANIFEST_CATEGORIES_SCHEMA
            )
        else:
            print("Warning: integration manifest has no categories")

        if not any(
            Path(path).name.lower() in {"readme", "readme.md", "info", "info.md"}
            for path in files
        ):
            raise ValueError("The repository has no information file")
        print("information file: passed")

        if (integration / "brand/icon.png").as_posix() in files:
            print("local brand icon: passed")
        else:
            print("Warning: no local brand icon; HACS's online brands fallback was not checked")
    except (TypeError, ValueError, subprocess.CalledProcessError) as err:
        print(f"HACS local validation failed: {err}", file=sys.stderr)
        return 1

    print("Local HACS checks passed; GitHub metadata and release checks were not run.")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve()))
