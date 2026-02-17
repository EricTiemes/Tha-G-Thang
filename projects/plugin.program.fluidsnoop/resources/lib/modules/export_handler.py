"""
Export Handler Module
Exports session data in multiple formats
"""

import os
import json
from datetime import datetime

class ExportHandler:
    """Handles multi-format exports"""
    
    def __init__(self, config):
        self.config = config
        
    def export_session(self, session_id, db, formats=None, pattern_type='all'):
        """Export session in specified formats"""
        if formats is None:
            formats = self.config.get_default_formats()
        
        results = {}
        
        for fmt in formats:
            if fmt == 'json':
                results['json'] = self._export_json(session_id, db)
            elif fmt == 'ai_handoff':
                results['ai_handoff'] = self._export_ai_handoff(session_id, db, pattern_type)
            elif fmt == 'compact':
                results['compact'] = self._export_compact(session_id, db)
            elif fmt == 'detailed':
                results['detailed'] = self._export_detailed(session_id, db, pattern_type)
        
        return results
    
    def _export_json(self, session_id, db):
        """Export raw JSON data"""
        session = db.get_session(session_id)
        events = db.get_events(session_id)
        
        export_data = {
            'session': session,
            'events': events,
            'exported': datetime.now().isoformat()
        }
        
        filename = f"session_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path = self.config.save_json(export_data, filename, 'exports')
        
        return {'format': 'json', 'path': path, 'count': len(events)}
    
    def _export_ai_handoff(self, session_id, db, pattern_type):
        """Export AI-friendly markdown report"""
        from modules.pattern_extract import PatternExtract
        
        session = db.get_session(session_id)
        patterns = PatternExtract(self.config).extract(session_id, db, pattern_type)
        
        lines = [
            '# FluidSnoop Analysis Report',
            '',
            f'**Session ID:** {session_id}',
            f'**Research Type:** {session.get("research_type", "unknown")}',
            f'**Target:** {session.get("target_addon", "unknown")}',
            f'**Generated:** {datetime.now().isoformat()}',
            '',
            '## Summary',
            ''
        ]
        
        # Add pattern summary
        if isinstance(patterns, dict) and 'summary' in patterns:
            summary = patterns['summary']
            lines.extend([
                f"- **Total Events:** {summary.get('total_events', 0)}",
                f"- **Modules Used:** {', '.join(summary.get('modules_used', []))}",
                ''
            ])
        
        # Add extracted patterns
        lines.append('## Extracted Patterns')
        lines.append('')
        
        if isinstance(patterns, dict):
            for key, pattern in patterns.items():
                if key == 'summary':
                    continue
                if isinstance(pattern, dict) and pattern.get('count', 0) > 0:
                    lines.append(f"### {key.replace('_', ' ').title()}")
                    lines.append(f"**Count:** {pattern.get('count', 0)}")
                    
                    if 'db_operations' in pattern and pattern['db_operations']:
                        lines.append('**Database Operations:**')
                        for op in pattern['db_operations'][:3]:
                            lines.append(f"- `{op.get('sql', '')[:80]}...`")
                    
                    if 'ui_feedback' in pattern and pattern['ui_feedback']:
                        lines.append('**UI Feedback:**')
                        for ui in pattern['ui_feedback'][:3]:
                            lines.append(f"- {ui.get('method', '')}: {ui.get('heading', '')}")
                    
                    if 'code_sequence' in pattern and pattern['code_sequence']:
                        lines.append('**Reusable Code:**')
                        lines.append('```python')
                        for code in pattern['code_sequence']:
                            lines.append(code)
                        lines.append('```')
                    
                    lines.append('')
        
        # Add raw event samples
        lines.extend([
            '## Event Samples',
            ''
        ])
        
        events = db.get_events(session_id, limit=10)
        for i, event in enumerate(events, 1):
            lines.append(f"### Event {i}")
            lines.append(f"- **Module:** {event.get('module', 'unknown')}")
            lines.append(f"- **Type:** {event.get('event_type', 'unknown')}")
            lines.append(f"- **Time:** {event.get('timestamp', 'unknown')}")
            data = event.get('data', {})
            if data:
                lines.append('```json')
                lines.append(json.dumps(data, indent=2, default=str)[:500])
                lines.append('```')
            lines.append('')
        
        content = '\n'.join(lines)
        filename = f"ai_handoff_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        path = os.path.join(self.config.exports_path, filename)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {'format': 'ai_handoff', 'path': path}
    
    def _export_compact(self, session_id, db):
        """Export compact summary"""
        session = db.get_session(session_id)
        stats = db.get_event_stats(session_id)
        
        lines = [
            f"Session: {session_id}",
            f"Type: {session.get('research_type', 'unknown')}",
            f"Target: {session.get('target_addon', 'unknown')}",
            f"Created: {session.get('created', 'unknown')}",
            f"Status: {session.get('status', 'unknown')}",
            "",
            f"Total Events: {stats.get('total', 0)}",
            "By Module:"
        ]
        
        for module, count in stats.get('by_module', {}).items():
            lines.append(f"  {module}: {count}")
        
        content = '\n'.join(lines)
        filename = f"compact_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path = os.path.join(self.config.exports_path, filename)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {'format': 'compact', 'path': path}
    
    def _export_detailed(self, session_id, db, pattern_type):
        """Export detailed report with full code"""
        from modules.pattern_extract import PatternExtract
        
        session = db.get_session(session_id)
        events = db.get_events(session_id)
        patterns = PatternExtract(self.config).extract(session_id, db, pattern_type)
        
        lines = [
            'FluidSnoop Detailed Export',
            '=' * 80,
            '',
            f'Session ID: {session_id}',
            f'Research Type: {session.get("research_type", "unknown")}',
            f'Target Addon: {session.get("target_addon", "unknown")}',
            f'Exported: {datetime.now().isoformat()}',
            ''
        ]
        
        # Full patterns section
        lines.extend([
            'EXTRACTED PATTERNS',
            '-' * 80,
            ''
        ])
        
        if isinstance(patterns, dict):
            for key, pattern in patterns.items():
                if key == 'summary':
                    continue
                if isinstance(pattern, dict):
                    lines.append(f"\n## {key.upper()}")
                    for k, v in pattern.items():
                        lines.append(f"{k}: {v}")
        
        # All events
        lines.extend([
            '',
            'ALL EVENTS',
            '-' * 80,
            ''
        ])
        
        for i, event in enumerate(events, 1):
            lines.append(f"\n--- Event {i} ---")
            for key, value in event.items():
                lines.append(f"{key}: {value}")
        
        content = '\n'.join(lines)
        filename = f"detailed_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path = os.path.join(self.config.exports_path, filename)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {'format': 'detailed', 'path': path, 'count': len(events)}
    
    def export_comparison(self, comparison_data, session_1_id, session_2_id):
        """Export comparison report"""
        lines = [
            '# FluidSnoop Comparison Report',
            '',
            f'**Session 1:** {session_1_id}',
            f'**Session 2:** {session_2_id}',
            f'**Generated:** {datetime.now().isoformat()}',
            '',
            '## Event Counts',
            f"- Session 1: {comparison_data.get('event_counts', {}).get('session_1', 0)}",
            f"- Session 2: {comparison_data.get('event_counts', {}).get('session_2', 0)}",
            '',
            '## Modules Used',
            f"- Session 1: {', '.join(comparison_data.get('modules_used', {}).get('session_1', []))}",
            f"- Session 2: {', '.join(comparison_data.get('modules_used', {}).get('session_2', []))}",
            '',
            '## Differences',
        ]
        
        for diff in comparison_data.get('differences', []):
            lines.append(f"- **{diff['type']}:** {diff['session_1_count']} vs {diff['session_2_count']}")
        
        if not comparison_data.get('differences'):
            lines.append('- No significant differences found')
        
        lines.extend([
            '',
            '## Similarities',
        ])
        
        for sim in comparison_data.get('similarities', []):
            lines.append(f"- **{sim['type']}:** {sim['count']} occurrences in both")
        
        content = '\n'.join(lines)
        filename = f"comparison_{session_1_id}_vs_{session_2_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        path = os.path.join(self.config.exports_path, filename)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {'format': 'comparison', 'path': path}