"""Local PHP integration tests; no requests or logs are sent to the real server."""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

OPTIONS = None


class UploadApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.domain = Path(cls.temp.name) / 'domain'
        cls.web = cls.domain / 'httpdocs'
        api = cls.web / 'touran/api'
        api.mkdir(parents=True)
        (api / 'upload-log.php').write_bytes(OPTIONS.endpoint.read_bytes())
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        cls.url = f'http://127.0.0.1:{port}/touran/api/upload-log.php'
        env = dict(os.environ, PHP_CLI_SERVER_WORKERS='4')
        cls.server = subprocess.Popen([OPTIONS.php, '-n', '-S', f'127.0.0.1:{port}', '-t', str(cls.web)],
                                      env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                      start_new_session=True)
        cls.http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            try:
                cls.http.open(cls.url, timeout=1)
            except urllib.error.HTTPError:
                return
            except OSError:
                if cls.server.poll() is not None:
                    break
                time.sleep(.05)
        cls.tearDownClass()
        raise RuntimeError('PHP server did not start')

    @classmethod
    def tearDownClass(cls):
        if cls.server.poll() is None:
            os.killpg(cls.server.pid, signal.SIGTERM)
            cls.server.wait(timeout=5)
        cls.temp.cleanup()

    def request(self, body=b'payload\n', install='fixture', **extra):
        headers = {'Content-Type': 'text/plain', 'X-Touran-Install': install,
                   'X-Touran-Session': 'test-session'}
        headers.update(extra)
        req = urllib.request.Request(self.url, data=body, headers=headers)
        try:
            response = self.http.open(req, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def stored(self, response):
        return self.domain / 'private/touran-logs' / response['stored']

    def test_method_and_size_limits(self):
        with self.assertRaises(urllib.error.HTTPError) as err:
            self.http.open(self.url)
        self.assertEqual(405, err.exception.code)
        for body in [b'', b'x' * (5 * 1024 * 1024 + 1)]:
            code, data = self.request(body)
            self.assertEqual(400, code)
            self.assertFalse(data['ok'])
        code, data = self.request(b'x' * (5 * 1024 * 1024), install='max-size')
        self.assertEqual(201, code)
        self.assertEqual(5 * 1024 * 1024, self.stored(data).stat().st_size)

    def test_private_storage_and_exact_payload(self):
        body = 'Rohdaten mit Öltemperatur\n'.encode()
        code, data = self.request(body, **{'X-Touran-Date': '2026-10-05'})
        self.assertEqual(201, code)
        self.assertEqual(body, self.stored(data).read_bytes())
        self.assertTrue(data['stored'].startswith('2026/10/05/fixture/'))
        self.assertFalse((self.web / 'touran/logs').exists())

    def test_dot_segments_cannot_escape_install_directory(self):
        for name in ['.', '..']:
            code, data = self.request(install=name)
            self.assertEqual(201, code)
            self.assertEqual('unknown-install', self.stored(data).parent.name)
            self.assertTrue(self.stored(data).is_relative_to(self.domain / 'private/touran-logs'))

    def test_invalid_calendar_date_falls_back(self):
        code, data = self.request(**{'X-Touran-Date': '2026-02-31'})
        self.assertEqual(201, code)
        today = datetime.now(ZoneInfo('Europe/Berlin')).strftime('%Y/%m/%d')
        self.assertTrue(data['stored'].startswith(today + '/'))

    def test_concurrent_live_batches_have_one_header_and_complete_records(self):
        def send(i):
            body = f'batch-{i:03d}\n'.encode()
            return self.request(body, install='live-concurrent', **{'X-Touran-Report': 'raw-can-live'})
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(send, range(24)))
        self.assertTrue(all(code == 201 for code, _ in results))
        path = self.stored(results[0][1])
        content = path.read_text()
        self.assertEqual(1, content.count('# TouranLive raw CAN live stream\n'))
        self.assertEqual(23, content.count('# batch_received='))
        for i in range(24):
            self.assertEqual(1, content.count(f'batch-{i:03d}\n'))
        self.assertEqual(path.name, (path.parent / 'LATEST_LIVE').read_text().strip())
        self.assertEqual(24, len((path.parent / 'index.ndjson').read_text().splitlines()))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--php', default='php')
    parser.add_argument('--endpoint', type=Path, default=Path(__file__).resolve().parents[1] / 'server/api/upload-log.php')
    OPTIONS, rest = parser.parse_known_args()
    unittest.main(argv=[__file__, *rest])
