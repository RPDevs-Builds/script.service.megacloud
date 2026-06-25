# Megacloud Decryptor Service for Kodi

`script.service.megacloud` is a Kodi add-on service that provides local, on-device decryption for Megacloud and Rabbitstream HLS video streams. 

This service was created to remove reliance on external third-party servers and ensure complete privacy and stability for Kodi users. It runs a lightweight HTTP server on port `4000` locally within your Kodi environment.

## Features
- **Local Decryption:** Converts Megacloud/Rabbitstream embed URLs into playable `.m3u8` master playlists directly on your device.
- **Anti-Bot Circumvention:** Automatically integrates with `script.service.flaresolverr` (running on port `8191`) to bypass Cloudflare and other advanced anti-bot protections.
- **Unified Logging & UI:** Replaces the standard `xbmc.log` pipeline with a custom `RotatingFileHandler` (max 5MB) to prevent Kodi log-spam. A built-in web viewer allows real-time log tailing directly at `http://127.0.0.1:4000/logs`.
- **Upstream Auto-Sync:** Features a fully automated CI/CD pipeline. Every night, the repository fetches the latest decryption algorithms from the upstream `mega-embed-2` project and auto-publishes an updated `.zip` release.

## Installation
1. Navigate to the **Releases** page of this repository.
2. Download the latest `script.service.megacloud-vX.X.X.zip` file.
3. Open Kodi and go to **Add-ons** > **Install from zip file**.
4. Select the downloaded `.zip` file.
5. *(Optional but highly recommended)*: Install `script.service.flaresolverr` to enable Cloudflare bypassing.

## Configuration & Settings
You can access the add-on settings via **Add-ons** > **My add-ons** > **Services** > **Megacloud Decryptor Service** > **Configure**.
- **Port:** Default is `4000`.
- **FlareSolverr Integration:** Enable fallback bypass logic and specify timeout parameters.
- **Advanced Logging:** Configure the custom log file path and log verbosity level (Debug, Info, Warning, Error). *(Note: Advanced settings are forced to `Level 0` visibility to ensure they are accessible regardless of Kodi UI settings).*

## How it Works
When enabled, the add-on runs silently in the background as an `xbmc.service`.

Other Kodi video add-ons (like Otaku) can route Megacloud embed URLs to the service by making a standard HTTP GET request:
```
http://127.0.0.1:4000/api/mega?url=https://megacloud.tv/embed-2/e-1/XXXXXXXX
```

The service will process the request, bypass Cloudflare (via FlareSolverr), decode the AES/Rabbitstream encryption layers, and return a JSON payload containing the raw media tracks.

## Upstream Synchronization
The core decryption logic in this add-on (`megacloud.py`) is powered by Python and is kept 1:1 with the original JavaScript logic via GitHub Actions. If the algorithm changes, the CI/CD pipeline uses `tools/transform.py` to automatically extract the new cryptographic parameters and rebuild the Python addon within 24 hours.
