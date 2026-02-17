plugin.program.fluiddev
├── INSTALL.md
├── README.md
├── addon.xml
├── changelog.txt
├── default.py
└── resources
    ├── __init__.py
    ├── entry_router.py
    ├── fanart.jpg
    ├── icon.png
    ├── lib
    │   ├── __init__.py
    │   ├── core
    │   │   ├── __init__.py
    │   │   ├── addon_scanner.py
    │   │   └── config.py
    │   ├── display
    │   │   ├── __init__.py
    │   │   └── main_menu.py
    │   ├── modules
    │   │   ├── __init__.py
    │   │   ├── module_dependency_mapper.py
    │   │   ├─ module_linter.py
    │   │   └── module_structure_analyzer.py
    │   └── {core,display,modules}
    ├── media
    ├── settings.xml
    └── templates
        └── template_dependency_audit.jsonaddon.program.fluiddev
        

Global scan, 
Specific focus global scan 
Scan from reports 

Selected addon's + selected hooks scan 
... 

Based on the common frustrations in Kodi forums and development guides, your **FluidDev** addon has the perfect opportunity to solve real, recurring problems for developers. The search results highlight several specific pain points that can be your targets.

Here’s a breakdown of common developer issues, how you can research them, and how to deliver the findings through your addon's "Research Dashboard."

### 🎯 Common Kodi Dev Pain Points to Target
The forum discussions reveal a clear pattern of difficulties, especially for developers who want to write clean, well-structured addons.

| Target Area | Common Problem (From Forums) | Suggested Research for FluidDev |
| :--- | :--- | :--- |
| **Dependency Management** | Installing modules like `requests` is often confusing and fails. | **Scan & Report**: Auto-analyze `addon.xml` and Python imports to flag missing/unavailable `script.module` dependencies. |
| **Code Structure & Quality** | Code becomes messy and hard to maintain; no guidance on organizing modules. | **Linting & Best Practices**: Integrate Python linters (e.g., Pylint, Flake8) to analyze structure, complexity, and adherence to style guides. |
| **Development Environment** | Hard to set up a clean dev environment separate from the main Kodi install. | **Environment Snapshot**: Create a portable profile of an addon’s dependencies and structure for easy cloning or testing. |
| **Addon Frameworks** | Confusion over which frameworks to use (e.g., simpleplugin, routing) and how. | **Framework Analysis**: Scan addons to detect and report which frameworks are used, providing real-world examples from the user's own library. |
| **Entry Point & Routing** | Developers struggle with how to correctly structure `default.py` and route user actions. | **Pattern Recognition**: Identify common routing patterns (e.g., use of `@route` decorators, `xbmcplugin` calls) and classify them. |

### 🔍 Research Methodology & Data Handling
To build these features, you'll need systematic ways to gather and process data from addons.

- **Global Scan (Discovery)**: Use the modular script we built to scan all addons for initial inventory (you've already done this).
- **Specific-Focus Scan (Analysis)**: Run targeted analyzers (linters, dependency checkers) on selected addons.
- **Template-Based Scanning**: Load "research templates" (e.g., a JSON config) that define what to look for, such as:
    ```json
    {
      "scan_id": "dependency_check",
      "target_files": ["addon.xml", "*.py"],
      "look_for": ["import requests", "script.module."],
      "analyzer": "dependency_matcher"
    }
    ```
- **Save & Load Searches**: Store scan configurations and results in a local JSON file or a simple SQLite database within your addon's `userdata` folder. This allows users to save a "research profile" and reload it later.

### 📊 Organizing Delivery: The Research Dashboard (Main Menu)
Your `main_menu` should function as a **command center**. Here’s a potential structure:

- **Global Overview**: A summary screen showing stats from the last full scan (e.g., "35 addons use frameworks, 17 are highly modular").
- **Targeted Analysis**:
    - *Quick Lint*: Run a selected linter on a chosen addon and show a report.
    - *Dependency Map*: Visualize an addon’s required modules and flag potential issues.
- **Report Gallery**: View, compare, and export previous analysis reports (text, JSON).
- **Research Templates**: Load, edit, and run saved scan configurations.

### 💡 AI-Style Summary & Recommendations
For each analysis, you can generate a concise "handover" summary that mimics an AI assistant:
> **Analysis of `plugin.video.cumination`**
> **Structure**: Highly modular (167 files). Uses `simpleplugin` framework.
> **Issues**: Two `script.module` dependencies are from unofficial repos.
> **Recommendation**: 1) Review dependency sources. 2) Consider implementing a caching pattern similar to addon X.
> **Commonality**: Uses the same routing pattern as 12 other video addons in your library.

### ✅ Recommended Implementation Path for FluidDev
1.  **Start with Linting**: Integrate a lightweight linter like `flake8` or `pylint`. This delivers immediate, tangible value by improving code quality.
2.  **Build the Dependency Checker**: This solves a top frustration and is highly useful.
3.  **Develop the Dashboard UI**: Use Kodi's window and control classes (`xbmcgui`) to create the main menu and report viewers.
4.  **Add Template System**: Allow saving/loading scan profiles to make research reusable.

My vision for a fast, lean research addon directly targets the gaps and frustrations evident in the developer community. By building these research tools, **FluidDev** can become an essential utility for anyone creating or maintaining Kodi addons.

