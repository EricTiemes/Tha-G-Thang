# FluidDev - Kodi Addon Development Analysis Tool

## Overview
FluidDev is a modular research dashboard for analyzing Kodi addon architectures. It helps developers understand, learn from, and improve their addons through systematic analysis.

## Features

### Level 1: Daily Tasks (Quick Scans)
- **Addon Health Check**: Run linter and dependency scan on selected addon
- **Structure Snapshot**: Quick overview of addon's module count and frameworks
- **Find Similar Addons**: Discover addons with similar architectural patterns

### Level 2: Targeted Research
- **Research by Template**: Load and run saved research templates
- **Analyze Dependencies**: Deep-dive into addon.xml and import statements
- **Compare 2 Addons**: Side-by-side structural comparison

### Level 3: Deep Research & Configuration
- **Template Manager**: Create and manage research templates
- **Global Scan Log**: View previous scan results
- **Global Scan**: Comprehensive analysis of all installed addons
- **Settings**: Configure analysis parameter


## Usage

### Quick Health Check
1. Launch FluidDev
2. Select "Addon Health Check"
3. Choose an addon to analyze
4. Review the structure and dependency report

### Global Scan
1. Select "Global Scan All Addons"
2. Confirm the scan
3. Wait for analysis to complete
4. Review the summary statistics

### Find Similar Addons
1. Select "Find Similar Addons"
2. Choose a reference addon
3. View addons with similar architectures

## Development

FluidDev is designed to be extensible. New analysis modules can be added to `resources/lib/modules/`.

### Adding a New Module
1. Create a new file in `resources/lib/modules/`
2. Implement the analysis logic
3. Add menu items in `main_menu.py`
4. Register actions in `execute_action()`

## License
GPL-3.0

## Version
1.0.3