# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon
import threading
from resources.lib.httpserver import ThreadedHTTPServer, HTTPRequestHandler
from resources.lib.logger import setup_logger, get_logger

log = get_logger()

ADDON = xbmcaddon.Addon('script.service.megacloud')

def get_settings():
    try:
        port_str = ADDON.getSetting('port')
        port = int(port_str) if port_str else 4000
    except ValueError:
        port = 4000
    
    autostart = ADDON.getSetting('autostart') != 'false'
    keys_url = ADDON.getSetting('keys_url') or "https://raw.githubusercontent.com/RPDevs-Builds/script.service.megacloud/master/keys/keys.json"
    
    fs_enable = ADDON.getSetting('fs_enable') == 'true'
    fs_url = ADDON.getSetting('fs_url') or "http://localhost:8191/v1"
    try:
        fs_timeout_str = ADDON.getSetting('fs_timeout')
        fs_timeout = int(fs_timeout_str) if fs_timeout_str else 30
    except ValueError:
        fs_timeout = 30
        
    enable_log = ADDON.getSetting('enable_log') != 'false'
    try:
        log_level_str = ADDON.getSetting('log_level')
        log_level = int(log_level_str) if log_level_str else 1
    except ValueError:
        log_level = 1
    log_path = ADDON.getSetting('log_path') or ""
        
    return port, autostart, keys_url, fs_enable, fs_url, fs_timeout, enable_log, log_level, log_path

class HTTPServerRunner(threading.Thread):
    def __init__(self, port, keys_url, fs_enable, fs_url, fs_timeout):
        super(HTTPServerRunner, self).__init__()
        self._port = port
        self._keys_url = keys_url
        self._fs_enable = fs_enable
        self._fs_url = fs_url
        self._fs_timeout = fs_timeout
        self._server = None

    def run(self):
        try:
            self._server = ThreadedHTTPServer(("", self._port), HTTPRequestHandler)
            self._server.keys_url = self._keys_url
            self._server.fs_enable = self._fs_enable
            self._server.fs_url = self._fs_url
            self._server.fs_timeout = self._fs_timeout
            log.info(f"Server started at port {self._port} (FlareSolverr enabled: {self._fs_enable})")
            self._server.serve_forever()
        except Exception as e:
            log.error(f"Server error: {str(e)}")
        finally:
            if self._server:
                self._server.server_close()
            log.info("Server closed")

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server = None

class MegacloudServiceMonitor(xbmc.Monitor):
    def __init__(self):
        super(MegacloudServiceMonitor, self).__init__()
        self._port, self._autostart, self._keys_url, self._fs_enable, self._fs_url, self._fs_timeout, self._enable_log, self._log_level, self._log_path = get_settings()
        setup_logger(self._enable_log, self._log_level, self._log_path)
        self._server_runner = None
        self._lock = threading.Lock()

    def start_server(self):
        with self._lock:
            if self._autostart and self._server_runner is None:
                log.info(f"Launching server on port {self._port}")
                self._server_runner = HTTPServerRunner(
                    self._port, self._keys_url, self._fs_enable, self._fs_url, self._fs_timeout
                )
                self._server_runner.start()

    def stop_server(self):
        with self._lock:
            if self._server_runner is not None:
                log.info("Stopping server")
                self._server_runner.stop()
                self._server_runner.join()
                self._server_runner = None

    def onSettingsChanged(self):
        new_port, new_autostart, new_keys_url, new_fs_enable, new_fs_url, new_fs_timeout, new_enable_log, new_log_level, new_log_path = get_settings()
        
        # Check if logging settings changed
        if (new_enable_log != self._enable_log or 
            new_log_level != self._log_level or 
            new_log_path != self._log_path):
            self._enable_log = new_enable_log
            self._log_level = new_log_level
            self._log_path = new_log_path
            setup_logger(self._enable_log, self._log_level, self._log_path)
            log.info("Logging configuration reloaded")
        
        restart = False
        with self._lock:
            if (new_port != self._port or 
                new_autostart != self._autostart or 
                new_keys_url != self._keys_url or
                new_fs_enable != self._fs_enable or
                new_fs_url != self._fs_url or
                new_fs_timeout != self._fs_timeout):
                restart = True
                
        if restart:
            log.info("Settings changed, restarting server...")
            self.stop_server()
            with self._lock:
                self._port = new_port
                self._autostart = new_autostart
                self._keys_url = new_keys_url
                self._fs_enable = new_fs_enable
                self._fs_url = new_fs_url
                self._fs_timeout = new_fs_timeout
            self.start_server()


if __name__ == '__main__':
    monitor = MegacloudServiceMonitor()
    if not monitor.waitForAbort(2):
        monitor.start_server()
        monitor.waitForAbort()
        monitor.stop_server()
