#!/usr/bin/env python3
"""Fail CI if the public HTTPS site does not match the checked-out sources."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import os
from pathlib import Path
import time
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from build_site import PAGE_FILES, ROOT, site_sources
from package_download import EXPECTED_SHA256, EXPECTED_SIZE, FILENAME

COPYRIGHT = b'Copyright ezuno.com by FAW GmbH.'
BASE_URL = 'https://www.ezuno.com/'
TEXT_SUFFIXES = {'.html', '.css', '.js', '.md', '.txt', '.properties', '.sha256'}


def check_source():
    for page in PAGE_FILES:
        data = (ROOT / page).read_bytes()
        if data.count(COPYRIGHT) != 1 or b'Copyright 2024 ezuno.com' in data:
            raise ValueError(f'{page}: expected one copyright notice without a year')
    print(f'Copyright notices checked on all {len(PAGE_FILES)} source pages.', flush=True)


def compare(path, actual, expected):
    if Path(path).suffix in TEXT_SUFFIXES or path == 'CNAME':
        actual = actual.replace(b'\r\n', b'\n')
        expected = expected.replace(b'\r\n', b'\n')
    if hashlib.sha256(actual).digest() != hashlib.sha256(expected).digest():
        raise ValueError(f'{path}: public content differs from the published revision')


def verify_once():
    revision = os.environ.get('GITHUB_SHA', 'local')
    cache_key = f'?verify={revision}-{time.time_ns()}'

    def fetch(path, method='GET', headers=None):
        request = Request(urljoin(BASE_URL, path) + cache_key,
                          method=method, headers=headers or {})
        return urlopen(request, timeout=20)

    def verify_source(source):
        path = source.relative_to(ROOT).as_posix()
        with fetch(path) as response:
            if response.status != 200:
                raise ValueError(f'{path}: unexpected HTTP {response.status}')
            compare(path, response.read(), source.read_bytes())

    # .nojekyll is a hosting marker, not a public resource.
    sources = [path for path in site_sources() if path.name != '.nojekyll']
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(verify_source, sources))

    installer = 'releases/' + FILENAME
    with fetch(installer + '.sha256') as response:
        compare(installer + '.sha256', response.read(),
                (EXPECTED_SHA256 + '  ' + FILENAME + '\n').encode('ascii'))
    with fetch(installer, method='HEAD') as response:
        if response.status != 200 or int(response.headers.get('Content-Length', 0)) != EXPECTED_SIZE:
            raise ValueError('Published installer has an unexpected size or HTTP status')
    with fetch(installer, headers={'Range': 'bytes=0-15'}) as response:
        expected_range = f'bytes 0-15/{EXPECTED_SIZE}'
        # Never download the full 412 MB package just to probe it.
        if response.status != 206 or response.headers.get('Content-Range') != expected_range:
            raise ValueError('Published installer does not support the expected byte range')
        with (ROOT / 'download-source' / (FILENAME + '.part001')).open('rb') as source:
            compare(installer, response.read(16), source.read(16))

    for url in ('https://ezuno.com/', 'http://ezuno.com/', 'http://www.ezuno.com/'):
        with urlopen(url, timeout=20) as response:
            if response.status != 200 or response.url != BASE_URL:
                raise ValueError(f'{url}: expected redirect to {BASE_URL}')
            compare('index.html', response.read(), (ROOT / 'index.html').read_bytes())
    print(f'HTTPS verification passed: {len(sources) + 1} matching resources, '
          'installer size/range and all domain redirects.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-source', action='store_true')
    args = parser.parse_args()
    check_source()
    if args.check_source:
        return
    for attempt in range(1, 7):
        try:
            verify_once()
            return
        except Exception as exc:
            print(f'Live verification attempt {attempt}/6: {exc}', flush=True)
            if attempt == 6:
                raise
            time.sleep(10)


if __name__ == '__main__':
    main()
