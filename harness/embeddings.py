"""Optional offline sentence-transformers adapter. Never installs or downloads."""
from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path, PureWindowsPath
import sys

ROOT = Path(__file__).resolve().parents[1]


def contained(relative):
    if not isinstance(relative, str) or not relative or PureWindowsPath(relative).drive or PureWindowsPath(relative).root:
        raise ValueError("Use a workspace-relative path.")
    parts = relative.replace("\\", "/").split("/")
    if any(part in {"", ".", ".."} or ":" in part for part in parts):
        raise ValueError("Unsafe relative path.")
    target = ROOT
    for part in parts:
        target = target / part
        stat = target.lstat()
        if target.is_symlink() or getattr(stat, "st_file_attributes", 0) & 0x400:
            raise ValueError("Path links are not allowed.")
    if not target.resolve().is_relative_to(ROOT):
        raise ValueError("Path escapes the workspace.")
    return target


def main():
    try:
        request = contained(sys.argv[1])
        if request.stat().st_size > 4 * 1024 * 1024:
            raise ValueError("Embedding request is too large.")
        data = json.loads(request.read_text(encoding="utf-8"))
        model_path = contained(data["model_path"])
        texts = data["texts"]
        if (not model_path.is_dir() or not isinstance(texts, list) or not 1 <= len(texts) <= 256
                or any(not isinstance(text, str) or len(text) > 8000 for text in texts)):
            raise ValueError("Invalid local model or input texts.")
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
        with contextlib.redirect_stdout(sys.stderr):
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(str(model_path), device="cpu",
                                        local_files_only=True, trust_remote_code=False)
            vectors = model.encode(texts, batch_size=16, normalize_embeddings=True,
                                   show_progress_bar=False).tolist()
        response = {"ok": True, "vectors": vectors}
    except Exception as error:
        response = {"ok": False, "error": type(error).__name__, "message": str(error)}
    print(json.dumps(response, allow_nan=False))


if __name__ == "__main__":
    main()
