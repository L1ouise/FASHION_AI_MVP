"""One-time script: delete fashion_images collection so batch_indexer can re-create it with deterministic IDs."""
import os, ssl

os.environ["CURL_CA_BUNDLE"] = ""
os.environ["REQUESTS_CA_BUNDLE"] = ""
ssl._create_default_https_context = ssl._create_unverified_context

import httpx
_orig = httpx.Client.__init__
def _patch(self, *a, **kw):
    kw["verify"] = False
    _orig(self, *a, **kw)
httpx.Client.__init__ = _patch

from pathlib import Path
env_path = Path(__file__).parent / ".env"
if env_path.is_file():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))

from qdrant_client import QdrantClient

url = os.getenv("QDRANT_URL")
key = os.getenv("QDRANT_API_KEY")
client = QdrantClient(url=url, api_key=key, timeout=30, prefer_grpc=False)

result = client.delete_collection("fashion_images")
print(f"delete_collection('fashion_images') -> {result}")
client.close()
print("Done. Now run: python src/batch_indexer.py")
