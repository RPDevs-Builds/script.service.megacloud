# -*- coding: utf-8 -*-
import os
import logging
from logging.handlers import RotatingFileHandler
import xbmc
import xbmcaddon
import xbmcvfs

_LOGGER = logging.getLogger('megacloud')
_LOGGER.propagate = False  # Prevent double logging if attached to root

def setup_logger(enable: bool, log_level: int, log_path: str):
    """
    Configure the custom RotatingFileHandler for the megacloud service.
    
    log_level mapping (from settings):
    0: Debug
    1: Info
    2: Warning
    3: Error
    """
    # Remove existing handlers
    for handler in _LOGGER.handlers[:]:
        _LOGGER.removeHandler(handler)
        handler.close()

    if not enable:
        _LOGGER.addHandler(logging.NullHandler())
        return

    # Map settings int to logging module levels
    level_map = {
        0: logging.DEBUG,
        1: logging.INFO,
        2: logging.WARNING,
        3: logging.ERROR
    }
    level = level_map.get(log_level, logging.INFO)
    _LOGGER.setLevel(level)

    # Ensure log directory exists
    if not log_path or not log_path.strip():
        # Fallback to profile addon_data
        addon = xbmcaddon.Addon('script.service.megacloud')
        log_path = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
    else:
        # Resolve special:// paths
        log_path = xbmcvfs.translatePath(log_path)

    os.makedirs(log_path, exist_ok=True)
    log_file = os.path.join(log_path, 'megacloud.log')

    # Setup RotatingFileHandler (Max 5MB, 1 Backup)
    try:
        handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=1, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s %(levelname)-8s [%(name)s] %(message)s')
        handler.setFormatter(formatter)
        _LOGGER.addHandler(handler)
        xbmc.log(f"[script.service.megacloud] Custom logging enabled -> {log_file}", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"[script.service.megacloud] Failed to setup custom logger: {e}", xbmc.LOGERROR)
        _LOGGER.addHandler(logging.NullHandler())

def get_logger():
    return _LOGGER
