# -*- coding: utf-8 -*-
import json
import re
import urllib.parse as urlparse
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from resources.lib.megacloud import extract_megacloud_sources

class HTTPRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        try:
            self.url = urlparse.urlsplit(self.path)
            self.query = dict(urlparse.parse_qsl(self.url.query))

            # Retrieve configured keys URL and FlareSolverr settings from the server instance
            keys_url = getattr(self.server, 'keys_url', None)
            fs_enable = getattr(self.server, 'fs_enable', False)
            fs_url = getattr(self.server, 'fs_url', 'http://localhost:8191/v1')
            fs_timeout = getattr(self.server, 'fs_timeout', 30)

            # Route 1: favicon.ico
            if self.url.path == "/favicon.ico":
                self.send_response(404)
                self.end_headers()
                return

            # Route 2: GET /get?url=<embedUrl>
            if self.url.path == "/get":
                embed_url = self.query.get("url")
                if not embed_url:
                    self.send_error_json(404, "No URL provided.")
                    return
                
                try:
                    embed_url = urlparse.unquote(embed_url)
                    url_parsed = urlparse.urlparse(embed_url)
                    if not url_parsed.scheme or not url_parsed.netloc:
                        raise ValueError()
                except Exception:
                    self.send_error_json(404, "Invalid URL provided.")
                    return

                try:
                    result = extract_megacloud_sources(
                        embed_url, referer="https://hianime.to/", keys_url=keys_url,
                        fs_enable=fs_enable, fs_url=fs_url, fs_timeout=fs_timeout
                    )
                    self.send_json(200, result)
                except Exception as e:
                    self.send_error_json(500, f"Decryption error: {str(e)}")
                return

            # Route 3: GET /:xrax (Matches any alphanumeric / hyphen / underscore route)
            xrax_match = re.match(r'^/([a-zA-Z0-9_-]+)$', self.url.path)
            if xrax_match:
                xrax = xrax_match.group(1)
                embed_url = f"https://megacloud.blog/embed-2/v3/e-1/{xrax}?k=1"
                try:
                    result = extract_megacloud_sources(
                        embed_url, referer="https://hianime.to/", keys_url=keys_url,
                        fs_enable=fs_enable, fs_url=fs_url, fs_timeout=fs_timeout
                    )
                    self.send_json(200, result)
                except Exception as e:
                    self.send_error_json(500, f"Decryption error: {str(e)}")
                return


            # Route 4: Fallback 404
            self.send_error_json(404, "Invalid API request")

        except Exception as e:
            self.send_error_json(500, f"Internal server error: {str(e)}")

    def send_json(self, status_code, data):
        try:
            body = json.dumps(data).encode('utf-8')
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            # Connection closed by client early
            pass

    def send_error_json(self, status_code, message):
        self.send_json(status_code, {"Error": message})

    def log_message(self, fmt, *args):
        # Silence default standard output request logging to avoid filling Kodi logs
        pass

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    allow_reuse_address = True
