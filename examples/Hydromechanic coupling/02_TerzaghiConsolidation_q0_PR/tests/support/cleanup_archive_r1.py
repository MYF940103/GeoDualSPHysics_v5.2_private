"""Lossless raw diagnostic CSV archive/restore; never deletes the raw source."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import zstandard as zstd

TESTS = Path(__file__).resolve().parents[1]
ROOT = (TESTS/'outputs').resolve()
PLAN = TESTS/'logs/cleanup_r1.plan.json'
CHUNK = 8*1024*1024


def digest_file(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--archive', type=int)
    mode.add_argument('--restore', type=int)
    args = parser.parse_args()
    plan = json.loads(PLAN.read_text(encoding='utf-8-sig'))
    index = args.archive if args.archive is not None else args.restore
    item = plan['files'][index]
    assert item['index'] == index and Path(plan['root']).resolve() == ROOT
    source = Path(item['path'])
    archive = Path(item['archive'])
    assert source.resolve().is_relative_to(ROOT) and archive.resolve().is_relative_to(ROOT)
    assert source.suffix == '.csv' and archive == Path(str(source)+'.zst')
    receipt = TESTS/'logs'/('cleanup_r1_file_%03d.json' % index)
    started = time.perf_counter()
    if args.archive is not None:
        assert source.is_file() and not source.is_symlink()
        assert not archive.exists() and not receipt.exists()
        before = source.stat()
        assert before.st_size == item['bytes']
        original_sha = hashlib.sha256()
        with source.open('rb') as incoming, archive.open('xb') as target:
            with zstd.ZstdCompressor(level=1, threads=2, write_checksum=True).stream_writer(target, closefd=False) as packed:
                while block := incoming.read(CHUNK):
                    original_sha.update(block)
                    packed.write(block)
        after = source.stat()
        assert (after.st_size, after.st_mtime_ns) == (before.st_size, before.st_mtime_ns)
        decoded_sha = hashlib.sha256()
        decoded_size = 0
        with archive.open('rb') as packed, zstd.ZstdDecompressor().stream_reader(packed) as decoded:
            while block := decoded.read(CHUNK):
                decoded_sha.update(block)
                decoded_size += len(block)
        assert decoded_size == before.st_size and decoded_sha.digest() == original_sha.digest()
        result = dict(verified=True, index=index, source=str(source), archive=str(archive),
                      source_bytes=before.st_size, source_sha256=original_sha.hexdigest(), source_mtime_ns=before.st_mtime_ns,
                      archive_bytes=archive.stat().st_size, archive_sha256=digest_file(archive),
                      decoded_sha256=decoded_sha.hexdigest(), plan_sha256=digest_file(PLAN),
                      elapsed_s=time.perf_counter()-started, original_deleted_by_this_program=False)
        with receipt.open('x', encoding='utf8') as stream:
            json.dump(result, stream, indent=2)
        print(json.dumps(result), flush=True)
    else:
        saved = json.loads(receipt.read_text())
        assert saved['verified'] and saved['source'] == str(source) and saved['archive'] == str(archive)
        assert not source.exists() and digest_file(archive) == saved['archive_sha256']
        restored_sha = hashlib.sha256()
        restored_size = 0
        with archive.open('rb') as packed, zstd.ZstdDecompressor().stream_reader(packed) as decoded, source.open('xb') as restored:
            while block := decoded.read(CHUNK):
                restored.write(block)
                restored_sha.update(block)
                restored_size += len(block)
        assert restored_size == saved['source_bytes'] and restored_sha.hexdigest() == saved['source_sha256']
        os.utime(source, ns=(saved['source_mtime_ns'], saved['source_mtime_ns']))
        print('Restored exact original bytes:', source)


if __name__ == '__main__':
    main()
