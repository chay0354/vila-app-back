import base64
import os
import sys
import uuid

import requests


def _extract_data_uri(data_uri: str) -> tuple[str, bytes]:
    if not data_uri.startswith("data:") or ";base64," not in data_uri:
        raise ValueError("Not a base64 data URI")
    header, b64 = data_uri.split(";base64,", 1)
    mime = header.replace("data:", "", 1)
    return mime, base64.b64decode(b64.encode("ascii"))


def main() -> int:
    base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:4000").rstrip("/")

    # Tiny 1x1 PNG
    png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGMA"
        "AQAABQABDQottAAAAABJRU5ErkJggg=="
    )
    png_bytes = base64.b64decode(png_b64)

    task_title = f"media-test-{uuid.uuid4().hex[:8]}"
    unit_id = "unit-1"
    created_date = "2025-12-18"

    files = {
        "media": ("test.png", png_bytes, "image/png"),
    }
    data = {
        "unit_id": unit_id,
        "title": task_title,
        "description": "media persist smoke test",
        "status": "פתוח",
        "created_date": created_date,
        "assigned_to": "test-user",
    }

    create_url = f"{base_url}/maintenance/tasks"
    r = requests.post(create_url, data=data, files=files, timeout=60)
    r.raise_for_status()
    created = r.json()
    task_id = created.get("id")
    if not task_id:
        raise RuntimeError(f"Create response missing id: {created}")

    get_url = f"{base_url}/maintenance/tasks/{task_id}"
    g = requests.get(get_url, timeout=60)
    g.raise_for_status()
    row = g.json()

    image_uri = row.get("image_uri") or row.get("imageUri")
    if not image_uri:
        raise RuntimeError("image_uri not found in DB row")

    mime, decoded = _extract_data_uri(image_uri)
    if mime != "image/png":
        raise RuntimeError(f"Unexpected mime: {mime}")
    if decoded != png_bytes:
        raise RuntimeError("Decoded bytes do not match uploaded bytes")

    print("OK: media persisted in DB")
    print(f"- task_id: {task_id}")
    print(f"- mime: {mime}")
    print(f"- bytes: {len(decoded)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"FAILED: {e}", file=sys.stderr)
        raise


