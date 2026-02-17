**TV Box Termux — install:**
```bash
pkg install fzf cronie rsync imagemagick
pip install gallery-dl yt-dlp mutagen paramiko
```

**Scripts to build next session:**
1. YT playlist picker → `yt-dlp` + `fzf` → selected downloads only
2. Reddit discovery → `gallery-dl` + `jq` → URLs saved to FLUID DB
3. Auto-tagger → `yt-dlp --dump-json` + `jq` → qwen bucket suggestion
4. Overnight sync → `rclone` + `cronie` → push downloads to cloud at 3am

**Firefox TV fixes:**
```
about:config
layout.css.devPixelsPerPx = 0.9    # adjust zoom
ui.ime.enabled = false              # suppress keyboard, mic still works
```

**Termux workarounds now possible:**
- `rclone mount` — mount cloud drive as local folder, Kodi browses it directly
- `cronie` + `yt-dlp` — queue downloads overnight, Kodi sees them in morning
- `ffmpeg` thumbnail strip/extract — feed Kodi cleaner artwork
- `openssh` — edit FLUID files on TV box from phone/PC via SSH
- `gallery-dl` + cron — auto-refresh Reddit image collections overnight
- `imagemagick` — batch resize thumbnails to Kodi's preferred dimensions

True — GoogleTV sideloading has real friction:
- Unknown sources toggle buried or missing
- APK installs blocked after OS updates
- Sideloaded apps disappear from launcher

**Add to next session — sideload helper scripts:**
- Auto-enable unknown sources via `adb` + Termux
- APK download + install one-liner
- Launcher visibility fix for sideloaded apps

Save for dedicated session — tokens gone. See you in 3 hours.