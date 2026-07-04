import argparse
import hashlib
import sys
import time
import uuid

from .config import StorageConfig
from .service import StorageService, StorageError


def verify(args: argparse.Namespace) -> int:
    config = StorageConfig.from_env()
    provider = config.provider

    valid, errors = config.is_valid()
    if not valid:
        for e in errors:
            print(f"CONFIG ERROR: {e}")
        return 1

    print(f"Provider:     {provider}")
    print(f"Bucket:       {config.bucket}")
    print()

    if provider == "mock":
        print("WARNING: STORAGE_PROVIDER=mock — no real storage.")
        print("Set STORAGE_PROVIDER=local and STORAGE_BASE_PATH to test local storage.")
        print()

    try:
        svc = StorageService(config=config)
    except Exception as exc:
        print(f"ERROR: Failed to initialize StorageService: {exc}")
        return 1

    test_name = f"__verify_test_{uuid.uuid4().hex[:12]}"
    test_data = b"Hello, Storage! This is a verification test."
    original_checksum = hashlib.sha256(test_data).hexdigest()

    print("=== Upload ===")
    t0 = time.monotonic()
    try:
        obj = svc.upload(test_name, test_data, content_type="text/plain")
    except StorageError as exc:
        print(f"FAILED: {exc}")
        return 1
    elapsed = (time.monotonic() - t0) * 1000
    print(f"Name:     {obj.name}")
    print(f"Size:     {obj.size} bytes")
    print(f"ETag:     {obj.etag}")
    print(f"Duration: {elapsed:.1f} ms")
    print()

    print("=== Exists ===")
    t0 = time.monotonic()
    exists = svc.exists(test_name)
    elapsed = (time.monotonic() - t0) * 1000
    print(f"Exists:   {exists}")
    print(f"Duration: {elapsed:.1f} ms")
    if not exists:
        print("FAILED: Object should exist after upload")
        return 1
    print()

    print("=== Download ===")
    t0 = time.monotonic()
    try:
        dl_obj, dl_data = svc.download(test_name)
    except StorageError as exc:
        print(f"FAILED: {exc}")
        return 1
    elapsed = (time.monotonic() - t0) * 1000
    dl_checksum = hashlib.sha256(dl_data).hexdigest()
    checksum_match = original_checksum == dl_checksum
    print(f"Size:     {len(dl_data)} bytes")
    print(f"Checksum: {'MATCH' if checksum_match else 'MISMATCH'}")
    print(f"Duration: {elapsed:.1f} ms")
    if not checksum_match:
        print("FAILED: Downloaded data checksum does not match")
        return 1
    print()

    print("=== Metadata ===")
    t0 = time.monotonic()
    try:
        meta = svc.metadata(test_name)
    except StorageError as exc:
        print(f"FAILED: {exc}")
        return 1
    elapsed = (time.monotonic() - t0) * 1000
    print(f"Name:     {meta.name}")
    print(f"Size:     {meta.size} bytes")
    print(f"Duration: {elapsed:.1f} ms")
    print()

    print("=== Delete ===")
    t0 = time.monotonic()
    try:
        svc.delete(test_name)
    except StorageError as exc:
        print(f"FAILED: {exc}")
        return 1
    elapsed = (time.monotonic() - t0) * 1000
    print(f"Duration: {elapsed:.1f} ms")
    print()

    print("=== Verify Deletion ===")
    exists = svc.exists(test_name)
    print(f"Exists:   {exists}")
    if exists:
        print("FAILED: Object should not exist after deletion")
        return 1
    print()

    print("=== Health ===")
    health = svc.health()
    print(f"Provider:     {health.provider}")
    print(f"Config valid: {health.config_valid}")
    print(f"Bucket:       {health.bucket}")
    print(f"Healthy:      {health.healthy}")
    print()

    print("All storage checks passed.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify storage service end-to-end",
    )
    parser.add_argument("--name", help="Object name to use (default: auto-generated)")
    parser.add_argument("--file", help="File to upload (default: inline test data)")

    args = parser.parse_args()

    sys.exit(verify(args))


if __name__ == "__main__":
    main()
