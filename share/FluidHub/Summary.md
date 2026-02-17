# FLUID Addon - Complete Architecture Summary

## ✅ Implemented Features

### 1. Three-Tier Settings System
- **Simple Mode**: Essential options only (quality, path, auto-deliver, progress)
- **Advanced Mode**: + Download/delivery modes, privacy options, context menu config
- **Pro Mode**: + Connection profiles, resume, retry, debug, encryption

### 2. Theme System
- **Default**: Standard Kodi dark theme
- **Chocolate**: Dark brown (#2D1B14) with cream text (#D4C4B0)
- Applied globally via ThemeManager, no module code changes needed

### 3. Flow Control (Your Request)
**Download Mode**: Background or Manual
**Delivery Mode**: Background, Manual, or Ask

**Combinations**:
- Background Download + Background Delivery = Fully automated
- Background Download + Manual Delivery = Download auto, user chooses where to copy
- Manual Download + Background Delivery = User chooses quality, auto-delivers
- Manual Download + Manual Delivery = Full control at each step

### 4. Privacy Features
- Auto-clean: Headers, cookies, referrer stripped from files
- Optional timestamp rename (20240215_143022.mp4 instead of title)
- Optional EXIF/metadata stripping
- Minimal meta storage: only video ID + thumb URL
- Private buckets with obfuscated names (Bucket_a3f9 instead of "Private")

### 5. Context Menu (Tidy, No Duplicates)
User configures which items appear (max 4):
- Quick Download (uses defaults)
- Download with Options (manual quality/path)
- Add to Favorites
- Find Extras

Smart behavior: adapts based on video state (playing, in favorites, etc.)

### 6. Module System
**Auto-discovered modules**:
- `downloader`: Core download with yt-dlp + Termux fallback
- `delivery`: Multi-path routing (keyword → local/SMB/WebDAV)
- `favorites`: Buckets, import/export, smart lists
- `playlist`: Smart playlist generation (placeholder)
- `meta`: Metadata fetching (placeholder)

Each module has:
- Enable/disable toggle
- Menu visibility toggle
- Independent settings

### 7. Multi-Path Delivery
**Rules-based routing**:
```json
{
  "name": "Music",
  "keywords": ["music", "song", "audio"],
  "paths": ["/storage/Music", "webdav://hidrive/Music"],
  "protocol": "local",
  "auto": true
}
```

Supports: Local, SMB, WebDAV (via Kodi VFS), extensible to SSH/cloud

### 8. Android Integration
- **Share Receiver**: Appears in Android share sheet (disabled by default)
- **Termux Fallback**: If yt-dlp unavailable in Kodi, hand off to Termux
- Service monitors for shared URLs

### 9. Database (Lightweight)
SQLite with tables:
- `favorites`: video_id, url, title, thumb_url, category, privacy_mode
- `categories`: id, name, obfuscated_name, is_private
- `downloads`: tracking for queue
- `delivery_queue`: async delivery tasks
- `meta_cache`: transcripts, extra thumbs (on-demand)

**Privacy**: Only URLs and IDs stored, no local file paths in private mode

### 10. Background Service
- Processes delivery queue every 30s
- Cleanup old records hourly
- Checks for shared URLs (Android)
- Resume/retry logic for failed deliveries

## 📁 File Structure

```
plugin.video.fluid/
├── addon.xml              # Addon manifest
├── default.py             # Main entry point
├── service.py             # Background service
├── context.py             # Right-click menu
├── resources/
│   ├── settings.xml       # Three-tier settings
│   ├── language/English/strings.po
│   ├── lib/
│   │   ├── core/          # System core
│   │   │   ├── config.py      # Settings manager
│   │   │   ├── database.py    # SQLite interface
│   │   │   ├── kodi_utils.py  # UI utilities + themes
│   │   │   ├── router.py      # URL dispatcher
│   │   │   └── logger.py      # Logging
│   │   └── modules/       # Feature modules
│   │       ├── downloader/engine.py
│   │       ├── delivery/router.py
│   │       ├── favorites/manager.py
│   │       ├── playlist/
│   │       └── meta/
│   └── data/              # Static data
```

## 🚀 Usage Flows

### Flow 1: Simple Background (Set & Forget)
1. User sets: Simple mode, quality=720p, auto-deliver=ON
2. Right-click video → Quick Download
3. Notification: "Download queued"
4. Background: Download → Auto-deliver to Music/Videos based on keywords
5. Final notification: "Complete"

### Flow 2: Manual Control (Per-Download Decisions)
1. User sets: Advanced mode, download=manual, delivery=ask
2. Right-click → Download with Options
3. Dialog: Select quality (720p/1080p/MP3)
4. Download with progress bar
5. Dialog: Select destinations (multi-select)
6. Delivery with progress

### Flow 3: Mixed (Background Download, Manual Delivery)
1. User sets: download=background, delivery=manual
2. Quick Download queues in background
3. Notification when download complete: "Deliver now?"
4. User chooses: Yes → select destinations, No → keep local

## 🔧 Next Steps for You

1. **Test Core**: Install in Kodi, verify basic download works
2. **Add yt-dlp**: Install script.module.yt-dlp dependency
3. **Configure Delivery**: Set up your HiDrive/WebDAV paths in settings
4. **Extend Modules**: Fill in playlist/meta placeholders
5. **Customize**: Add more delivery protocols (SSH, specific cloud APIs)

## 📝 Key Design Decisions

1. **No hardcoded colors**: ThemeManager.get_color() everywhere
2. **Modular menus**: Only enabled+visible modules show
3. **Privacy by default**: Minimal data retention, obfuscation options
4. **Flexible flow**: User controls automation level per step
5. **Android-native**: Share receiver, Termux fallback
6. **Kodi-native**: Uses xbmcvfs for all file operations (cross-platform)

## ⚠️ Known Limitations

1. yt-dlp dependency must be installed separately (or use Termux fallback)
2. WebDAV/SMB credentials stored in plain text (Pro mode: encryption option)
3. Background service requires Kodi to stay running
4. No built-in player (uses Kodi's player for STRM files)

## 🎯 Ready for Testing

The addon is structurally complete and ready for:
- Installation testing
- Settings verification
- Download flow testing (with yt-dlp installed)
- Delivery routing testing
- Favorites import/export testing

Playlist and Meta modules are stubs for future development.