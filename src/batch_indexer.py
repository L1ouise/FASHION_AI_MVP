"""
batch_indexer.py — Index catalog images into Qdrant (production-ready).

Features:
  - Deterministic point IDs (SHA-256 of filename) → no duplicate indexing
  - Skips images already present in the collection
  - Validates collection vector dimensions before uploading
  - Structured logging, per-image error handling, final summary
  - Configurable via .env or environment variables:
      QDRANT_URL, QDRANT_API_KEY, HF_TOKEN,
      COLLECTION_NAME, BATCH_SIZE, THUMB_MAX_WIDTH

Usage:
    python src/batch_indexer.py
"""
from __future__ import annotations

import hashlib
import io
import base64
import logging
import os
import ssl
import sys
import time
import uuid
from pathlib import Path

# ─── SSL workaround (corporate proxy / self-signed cert) ─────────────────────
os.environ.setdefault("CURL_CA_BUNDLE", "")
os.environ.setdefault("REQUESTS_CA_BUNDLE", "")
os.environ.setdefault("HF_HUB_DISABLE_SSL_VERIFY", "1")
ssl._create_default_https_context = ssl._create_unverified_context

import httpx  # noqa: E402

_orig_client_init = httpx.Client.__init__
def _patched_client_init(self, *a, **kw):
    kw["verify"] = False
    _orig_client_init(self, *a, **kw)
httpx.Client.__init__ = _patched_client_init

_orig_async_init = httpx.AsyncClient.__init__
def _patched_async_init(self, *a, **kw):
    kw["verify"] = False
    _orig_async_init(self, *a, **kw)
httpx.AsyncClient.__init__ = _patched_async_init

import requests  # noqa: E402
requests.packages.urllib3.disable_warnings()
_orig_request = requests.Session.request
def _patched_request(self, *a, **kw):
    kw.setdefault("verify", False)
    return _orig_request(self, *a, **kw)
requests.Session.request = _patched_request
# ──────────────────────────────────────────────────────────────────────────────

from PIL import Image  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402
from qdrant_client import QdrantClient  # noqa: E402
from qdrant_client.models import (  # noqa: E402
    Distance,
    PointStruct,
    VectorParams,
)

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("batch_indexer")

# ─── Paths ────────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "Data" / "catalog"
ENV_PATH = ROOT_DIR / ".env"

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
EXPECTED_VECTOR_SIZE = 512
MODEL_NAME = "clip-ViT-B-32"


# ═══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def load_env(path: Path) -> None:
    """Load key=value pairs from a .env file into os.environ (setdefault)."""
    if not path.is_file():
        return
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def deterministic_id(filename: str) -> str:
    """SHA-256 of the filename → deterministic UUID point ID."""
    h = hashlib.sha256(filename.encode("utf-8")).hexdigest()
    # Use first 32 hex chars to build a valid UUID
    return str(uuid.UUID(h[:32]))


def make_thumbnail_b64(img: Image.Image, max_width: int) -> str:
    """Resize to max_width and return base64-encoded JPEG."""
    ratio = max_width / img.width
    thumb = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
    if thumb.mode in ("RGBA", "LA", "P"):
        thumb = thumb.convert("RGB")
    buf = io.BytesIO()
    thumb.save(buf, format="JPEG", quality=80)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def get_existing_filenames(client: QdrantClient, collection: str) -> set[str]:
    """Scroll through the collection and return a set of already-indexed filenames."""
    existing: set[str] = set()
    offset = None
    while True:
        results, offset = client.scroll(
            collection_name=collection,
            limit=256,
            offset=offset,
            with_payload=["filename"],
            with_vectors=False,
        )
        for pt in results:
            fn = pt.payload.get("filename")
            if fn:
                existing.add(fn)
        if offset is None:
            break
    return existing


def validate_collection(client: QdrantClient, name: str) -> None:
    """Ensure collection exists and its vector size matches EXPECTED_VECTOR_SIZE."""
    collections = {c.name for c in client.get_collections().collections}

    if name not in collections:
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=EXPECTED_VECTOR_SIZE, distance=Distance.COSINE),
        )
        log.info("Created collection '%s' (dim=%d, COSINE)", name, EXPECTED_VECTOR_SIZE)
        return

    info = client.get_collection(collection_name=name)
    vec_cfg = info.config.params.vectors
    # vec_cfg can be a VectorParams or a dict of named vectors
    if hasattr(vec_cfg, "size"):
        actual_size = vec_cfg.size
    elif isinstance(vec_cfg, dict):
        first = next(iter(vec_cfg.values()))
        actual_size = first.size
    else:
        log.warning("Could not determine vector size — skipping validation")
        return

    if actual_size != EXPECTED_VECTOR_SIZE:
        log.error(
            "Collection '%s' has dim=%d but model produces dim=%d. "
            "Delete the collection or switch model.",
            name, actual_size, EXPECTED_VECTOR_SIZE,
        )
        sys.exit(1)

    log.info("Collection '%s' OK (dim=%d)", name, actual_size)


# ═══════════════════════════════════════════════════════════════════════════════
#  Main pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    t0 = time.perf_counter()

    # ── Config ────────────────────────────────────────────────────────────
    load_env(ENV_PATH)

    collection   = os.getenv("COLLECTION_NAME", "fashion_images")
    batch_size   = int(os.getenv("BATCH_SIZE", "64"))
    thumb_width  = int(os.getenv("THUMB_MAX_WIDTH", "400"))
    qdrant_url   = os.getenv("QDRANT_URL")
    qdrant_key   = os.getenv("QDRANT_API_KEY")
    hf_token     = os.getenv("HF_TOKEN")

    # Pass HF token to huggingface_hub so model download is authenticated
    if hf_token:
        os.environ["HF_TOKEN"] = hf_token
        os.environ["HUGGING_FACE_HUB_TOKEN"] = hf_token
        log.info("HF_TOKEN set — authenticated downloads enabled")
    else:
        log.warning(
            "No HF_TOKEN found. Downloads are unauthenticated (rate-limited). "
            "Set HF_TOKEN in .env to suppress this."
        )

    # ── Qdrant client ─────────────────────────────────────────────────────
    if qdrant_url:
        log.info("Connecting to Qdrant Cloud: %s", qdrant_url)
        client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_key,
            timeout=120,
            prefer_grpc=False,
        )
    else:
        log.info("Connecting to Qdrant localhost:6333")
        client = QdrantClient(host="localhost", port=6333, timeout=120)

    try:
        # ── Collection validation ─────────────────────────────────────────
        validate_collection(client, collection)

        # ── Load CLIP model ───────────────────────────────────────────────
        log.info("Loading model '%s' ...", MODEL_NAME)
        try:
            model = SentenceTransformer(MODEL_NAME)
        except Exception as exc:
            log.error("Failed to load model '%s': %s", MODEL_NAME, exc)
            sys.exit(1)

        dim = model.get_sentence_embedding_dimension()
        if dim is None:
            # CLIP models may not report dim; probe with a dummy encode
            dim = len(model.encode("test"))
        log.info("Model loaded — embedding dim=%d", dim)
        if dim != EXPECTED_VECTOR_SIZE:
            log.error(
                "Model dim (%d) != collection dim (%d). Aborting.", dim, EXPECTED_VECTOR_SIZE
            )
            sys.exit(1)

        # ── Discover images ───────────────────────────────────────────────
        if not DATA_DIR.is_dir():
            log.error("Data directory not found: %s", DATA_DIR)
            sys.exit(1)

        all_images = sorted(
            p for p in DATA_DIR.iterdir()
            if p.suffix.lower() in SUPPORTED_EXTENSIONS
        )
        log.info("Found %d images in %s", len(all_images), DATA_DIR)

        if not all_images:
            log.warning("Nothing to index — exiting")
            return

        # ── De-duplication: skip already-indexed ──────────────────────────
        log.info("Checking for already-indexed images ...")
        existing_filenames = get_existing_filenames(client, collection)
        to_index = [p for p in all_images if p.name not in existing_filenames]
        skipped = len(all_images) - len(to_index)

        if skipped:
            log.info("Skipping %d already-indexed images", skipped)
        if not to_index:
            log.info("All images already indexed — nothing to do")
            return

        log.info("Indexing %d new images (batch_size=%d)", len(to_index), batch_size)

        # ── Process & upload ──────────────────────────────────────────────
        points: list[PointStruct] = []
        ok_count = 0
        fail_count = 0
        batch_count = 0
        total = len(to_index)

        for idx, img_path in enumerate(to_index, 1):
            try:
                with Image.open(img_path) as img:
                    img.load()
                    vector = model.encode(img).tolist()
                    thumb_b64 = make_thumbnail_b64(img, thumb_width)

                points.append(
                    PointStruct(
                        id=deterministic_id(img_path.name),
                        vector=vector,
                        payload={
                            "filename": img_path.name,
                            "image_path": str(img_path),
                            "thumb_b64": thumb_b64,
                        },
                    )
                )
                ok_count += 1

                if idx % 50 == 0 or idx == total:
                    log.info("  encoded %d/%d", idx, total)

            except Exception as exc:
                fail_count += 1
                log.warning("  SKIP %s — %s", img_path.name, exc)
                continue

            # Flush batch
            if len(points) >= batch_size:
                try:
                    client.upsert(collection_name=collection, points=points)
                    batch_count += 1
                    log.info("  batch %d uploaded (%d points)", batch_count, len(points))
                except Exception as exc:
                    fail_count += len(points)
                    ok_count -= len(points)
                    log.error("  batch upload FAILED: %s", exc)
                points = []

        # Final flush
        if points:
            try:
                client.upsert(collection_name=collection, points=points)
                batch_count += 1
                log.info("  batch %d uploaded (%d points)", batch_count, len(points))
            except Exception as exc:
                fail_count += len(points)
                ok_count -= len(points)
                log.error("  final batch upload FAILED: %s", exc)

        # ── Summary ───────────────────────────────────────────────────────
        elapsed = time.perf_counter() - t0
        log.info("=" * 55)
        log.info("  INDEXING COMPLETE")
        log.info("  Images found       : %d", len(all_images))
        log.info("  Already indexed     : %d", skipped)
        log.info("  Newly indexed       : %d", ok_count)
        log.info("  Failed / skipped    : %d", fail_count)
        log.info("  Batches uploaded    : %d", batch_count)
        log.info("  Elapsed time        : %.1fs", elapsed)
        log.info("=" * 55)

    finally:
        # Explicitly close client to avoid the RuntimeWarning about
        # interrupted HTTP connections on Qdrant Cloud.
        try:
            client.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()