"""Actual Chromium + local HTTP redirects; never contacts a publisher."""
import shutil
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from urllib.parse import urlsplit
from scripts.tennis_publisher_holds import install_browser_hold


class BrowserRedirectBoundaryTests(unittest.TestCase):
    def test_real_redirect_and_subresource_hold_before_dispatch(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            if os.environ.get('TENNIS_BROWSER_BOUNDARY_REQUIRED')=='1':
                raise
            self.skipTest('Playwright unavailable; run explicit browser guard CI')
        chromium=shutil.which('chromium') or shutil.which('chromium-browser')
        # CI installs Playwright Chromium; local system Chromium is optional.
        seen=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self):
                seen.append((self.headers.get('Host'),self.path))
                port=self.server.server_port
                if self.path in ('/held-hop','/image-hop'):
                    self.send_response(302)
                    self.send_header('Location',f'http://localhost:{port}/held-target')
                    self.end_headers()
                elif self.path=='/chain':
                    self.send_response(302);self.send_header('Location','/held-hop');self.end_headers()
                elif self.path=='/allowed-hop':
                    self.send_response(302);self.send_header('Location','/allowed-final');self.end_headers()
                else:
                    body=(b'<html><body>allowed<img src="/image-hop"></body></html>'
                          if self.path=='/page' else b'<html><body>allowed final</body></html>')
                    self.send_response(200);self.send_header('Content-Type','text/html')
                    self.end_headers();self.wfile.write(body)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_port}'
        def local_policy(url):
            return 'Synthetic held host' if urlsplit(url).hostname=='localhost' else None
        try:
            with patch('scripts.tennis_publisher_holds.permission_hold_reason',side_effect=local_policy):
                with sync_playwright() as pw:
                    try:
                        browser=pw.chromium.launch(headless=True,**({'executable_path':chromium} if chromium else {}))
                    except Exception as exc:
                        if os.environ.get('TENNIS_BROWSER_BOUNDARY_REQUIRED')=='1':
                            raise
                        self.skipTest('Chromium unavailable in local execution sandbox: '+str(exc).splitlines()[0])
                    page=browser.new_page(service_workers='block');install_browser_hold(page)
                    for path in ('/held-hop','/chain'):
                        with self.assertRaises(Exception):page.goto(base+path,timeout=5000)
                    page.goto(base+'/allowed-hop',timeout=5000)
                    self.assertIn('allowed final',page.locator('body').inner_text())
                    page.goto(base+'/page',wait_until='networkidle',timeout=5000)
                    self.assertIn('allowed',page.locator('body').inner_text())
                    browser.close()
            self.assertTrue(any(path=='/held-hop' for _,path in seen))
            self.assertTrue(any(path=='/image-hop' for _,path in seen))
            self.assertTrue(any(path=='/allowed-final' for _,path in seen))
            self.assertFalse(any(path=='/held-target' or host.startswith('localhost:') for host,path in seen),seen)
        finally:
            server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()
