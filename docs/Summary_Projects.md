### Projects

1. 
#### **FLUID** (User/Management Addon)

* **A personal organizer for Kodi content that falls outside traditional library scraping, such as YouTube tutorials, Twitch streams, and web videos.
* **Functions:** * **Collections** Saves videos into custom collections (= Favorites) via right-click.
* **Context-Aware Menus:** Intelligent options like "Find Similar" (related content), "Move" (transfer between buckets), and "Remove".
* **Learning Engine:** Adapts to user organizational habits to suggest automatic placements over time.


* **Aim & Vision:** To bridge the gap between "standard" metadata-rich media and the "unscrapeable" web content by creating an intuitive, usage-based organization system that "flows" naturally from how you already use Kodi.

2. (Concept, Idea) 
#### **FLUID MEDIA SEARCH** (Discovery/Intelligent Search)

* **A cross-platform search engine designed to extract, score, and bundle media from public APIs and scrapers without requiring logins.
* **Functions:** * **Multi-Source Extraction:** Pulls data from YouTube (yt-dlp), Reddit (PRAW), and existing Kodi addons.
* **Intelligent Processing:** Features a scoring algorithm for relevance, "FuzzyWuzzy" deduplication, and automated text summarization.
* **Export Options:** Can output findings as AI-ready bundles, M3U playlists, or directly into FLUID buckets.


* **Aim & Vision:** To provide an intelligent, unified search layer for Kodi that treats the internet as a local library, prioritizing "AI-style" output and streamlined content gathering.
... 

3. (Recent started with Dev) 
#### **FLUIDDEV** (Developer Tooling)

* **A research and analysis dashboard for Kodi addon developers to audit code, map dependencies, and analyze structure.
* **Functions:** * **Code Auditing:** Includes a linter (e.g., flake8/pylint) and a dependency mapper to identify external module requirements.
* **Template-Based Analysis:** Uses JSON templates to run preset "Quick" or "FullDev" scans (e.g., `structure_quick.json`).
* **Report Gallery:** Stores and compares analysis results to track development changes or compare different addons.


* **Vision:** To solve common developer frustrations—like dependency "hell" and lack of structural oversight—by acting as a "quiet assistant" for code maintenance and research.

---

### 2. Future Ideas & Research Keywords

#### **Near Future Ideas**

* **Hybrid AI Recommendations:** Integrate local LLMs to generate the "AI-style handover" summaries for search results or code audits.
* **Automatic "Bucket" Curation:** Have FLUID suggest bucket creation based on frequency of specific search terms in Fluid Media Search.
* **Hook Lifecycle Analysis:** For FluidDev, implement real-time tracing of Kodi's internal hooks to see exactly how and when an addon interacts with the system.
* **FTS5 Search Cache:** Implement SQLite-utils FTS5 for lightning-fast full-text searches across all saved media metadata.

#### **Useful Kodi Functions & Keywords (Search Specific)**

| Category | Keywords / Functions | Use Case |
| --- | --- | --- |
| **Input/UI** | `xbmc.Keyboard`, `get_user_input` | Triggering search queries via the OSK. |
| **Orchestration** | `xbmcplugin.addDirectoryItem`, `setResolvedUrl` | Displaying search results as playable Kodi items. |
| **Metadata** | `ListItem.setInfo`, `ListItem.setArt` | Populating results with plot, genre, and thumbnails. |
| **Files/VFS** | `xbmcvfs.listdir`, `xbmcvfs.File` | Searching local network storage for unscraped files. |
| **Internal Ops** | `xbmc.executebuiltin`, `JSON-RPC` | Interacting with other addons or system settings programmatically. |
| **Caching** | `sqlite-utils`, `FTS5`, `hashlib` | Indexing search results to avoid redundant API calls. |