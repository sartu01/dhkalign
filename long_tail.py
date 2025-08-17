#!/usr/bin/env python3
"""
WRAITH Operational Utilities
Live log monitoring, analytics CLI, and deployment helpers for DHK Align WRAITH system.
"""

import json
import time
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, Any, List
import subprocess

# ANSI Colors for terminal output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def print_banner():
    """Print WRAITH system banner"""
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
╦ ╦╦═╗╔═╗╦╔╦╗╦ ╦  ╔═╗╔═╗╔═╗╦═╗╔═╗╔╦╗╦╔═╗╔╗╔╔═╗╦    
║║║╠╦╝╠═╣║ ║ ╠═╣  ║ ║╠═╝║╣ ╠╦╝╠═╣ ║ ║║ ║║║║╠═╣║    
╚╩╝╩╚═╩ ╩╩ ╩ ╩ ╩  ╚═╝╩  ╚═╝╩╚═╩ ╩ ╩ ╩╚═╝╝╚╝╩ ╩╩═╝  
                                                    
DHK Align WRAITH - Operational Command Center
{Colors.END}
"""
    print(banner)

class LogTailer:
    """Real-time log monitoring with intelligent filtering"""
    
    def __init__(self, log_dir: Path = Path("logs")):
        self.log_dir = log_dir
        self.log_files = {
            'main': log_dir / "dhk_align.log",
            'translations': log_dir / "translations.jsonl", 
            'performance': log_dir / "performance.jsonl",
            'errors': log_dir / "errors.log"
        }
    
    def tail_live(self, log_type: str = "all", filter_event: str = None):
        """Live tail logs with filtering and color coding"""
        print_banner()
        print(f"{Colors.GREEN}🔍 WRAITH Live Log Monitor{Colors.END}")
        print(f"Monitoring: {Colors.BOLD}{log_type}{Colors.END}")
        if filter_event:
            print(f"Event Filter: {Colors.YELLOW}{filter_event}{Colors.END}")
        print(f"Log Directory: {self.log_dir}")
        print("=" * 80)
        
        if log_type == "all":
            self._tail_all_logs(filter_event)
        else:
            self._tail_single_log(log_type, filter_event)
    
    def _tail_all_logs(self, filter_event: str = None):
        """Monitor all log files simultaneously"""
        file_positions = {}
        
        # Initialize file positions
        for log_name, log_path in self.log_files.items():
            if log_path.exists():
                file_positions[log_name] = log_path.stat().st_size
            else:
                file_positions[log_name] = 0
        
        print(f"{Colors.BLUE}Watching all log files... (Ctrl+C to stop){Colors.END}\n")
        
        try:
            while True:
                for log_name, log_path in self.log_files.items():
                    if not log_path.exists():
                        continue
                    
                    current_size = log_path.stat().st_size
                    if current_size > file_positions[log_name]:
                        # New content available
                        with open(log_path, 'r') as f:
                            f.seek(file_positions[log_name])
                            new_lines = f.readlines()
                            
                        for line in new_lines:
                            self._format_and_print_line(line.strip(), log_name, filter_event)
                        
                        file_positions[log_name] = current_size
                
                time.sleep(0.5)  # Check every 500ms
                
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Log monitoring stopped.{Colors.END}")
    
    def _tail_single_log(self, log_type: str, filter_event: str = None):
        """Monitor a single log file"""
        log_path = self.log_files.get(log_type)
        if not log_path or not log_path.exists():
            print(f"{Colors.RED}Error: Log file {log_path} not found{Colors.END}")
            return
        
        print(f"{Colors.BLUE}Watching {log_path}... (Ctrl+C to stop){Colors.END}\n")
        
        # Start from end of file
        file_position = log_path.stat().st_size
        
        try:
            while True:
                current_size = log_path.stat().st_size
                if current_size > file_position:
                    with open(log_path, 'r') as f:
                        f.seek(file_position)
                        new_lines = f.readlines()
                    
                    for line in new_lines:
                        self._format_and_print_line(line.strip(), log_type, filter_event)
                    
                    file_position = current_size
                
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Log monitoring stopped.{Colors.END}")
    
    def _format_and_print_line(self, line: str, log_name: str, filter_event: str = None):
        """Format and colorize log lines"""
        if not line.strip():
            return
        
        # Try to parse as JSON for structured logs
        try:
            if log_name in ['translations', 'performance'] and line.startswith('{'):
                log_entry = json.loads(line)
                event_type = log_entry.get('event_type', '')
                
                # Apply event filter
                if filter_event and filter_event not in event_type:
                    return
                
                self._print_structured_log(log_entry, log_name)
            else:
                # Plain text log
                if filter_event and filter_event not in line:
                    return
                self._print_plain_log(line, log_name)
                
        except json.JSONDecodeError:
            # Not JSON, treat as plain text
            if filter_event and filter_event not in line:
                return
            self._print_plain_log(line, log_name)
    
    def _print_structured_log(self, log_entry: Dict, log_name: str):
        """Pretty print structured JSON logs"""
        timestamp = log_entry.get('timestamp', datetime.now().isoformat())
        level = log_entry.get('level', 'INFO')
        message = log_entry.get('message', '')
        event_type = log_entry.get('event_type', 'unknown')
        
        # Color by log level
        level_colors = {
            'ERROR': Colors.RED,
            'WARNING': Colors.YELLOW, 
            'INFO': Colors.GREEN,
            'DEBUG': Colors.BLUE
        }
        level_color = level_colors.get(level, Colors.WHITE)
        
        # Color by log source
        source_colors = {
            'translations': Colors.CYAN,
            'performance': Colors.MAGENTA,
            'errors': Colors.RED
        }
        source_color = source_colors.get(log_name, Colors.WHITE)
        
        print(f"{Colors.BOLD}{timestamp[:19]}{Colors.END} "
              f"{source_color}[{log_name.upper()}]{Colors.END} "
              f"{level_color}{level}{Colors.END} "
              f"{Colors.YELLOW}{event_type}{Colors.END} - {message}")
        
        # Print key metrics if available
        metrics = []
        if 'confidence' in log_entry:
            metrics.append(f"confidence: {log_entry['confidence']:.2f}")
        if 'processing_time_ms' in log_entry:
            metrics.append(f"time: {log_entry['processing_time_ms']:.1f}ms")
        if 'method' in log_entry:
            metrics.append(f"method: {log_entry['method']}")
        
        if metrics:
            print(f"  {Colors.BLUE}├─{Colors.END} {' | '.join(metrics)}")
    
    def _print_plain_log(self, line: str, log_name: str):
        """Print plain text logs with coloring"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Color by content
        if "ERROR" in line or "❌" in line:
            color = Colors.RED
        elif "WARNING" in line or "⚠️" in line:
            color = Colors.YELLOW
        elif "SUCCESS" in line or "✅" in line:
            color = Colors.GREEN
        else:
            color = Colors.WHITE
        
        source_colors = {
            'main': Colors.BLUE,
            'errors': Colors.RED
        }
        source_color = source_colors.get(log_name, Colors.WHITE)
        
        print(f"{Colors.BOLD}{timestamp}{Colors.END} "
              f"{source_color}[{log_name.upper()}]{Colors.END} "
              f"{color}{line}{Colors.END}")

class AnalyticsCLI:
    """Command-line analytics for WRAITH system"""
    
    def __init__(self, log_dir: Path = Path("logs")):
        self.log_dir = log_dir
        self.translations_log = log_dir / "translations.jsonl"
        self.performance_log = log_dir / "performance.jsonl"
        self.errors_log = log_dir / "errors.log"
    
    def generate_report(self, hours: int = 24):
        """Generate comprehensive system report"""
        print_banner()
        print(f"{Colors.GREEN}📊 WRAITH System Analytics Report{Colors.END}")
        print(f"Time Period: Last {hours} hours")
        print("=" * 80)
        
        # Translation Analytics
        translation_stats = self._analyze_translations(hours)
        self._print_translation_report(translation_stats)
        
        # Performance Analytics  
        performance_stats = self._analyze_performance(hours)
        self._print_performance_report(performance_stats)
        
        # Error Analytics
        error_stats = self._analyze_errors(hours)
        self._print_error_report(error_stats)
        
        # System Health Summary
        self._print_health_summary(translation_stats, performance_stats, error_stats)
    
    def _analyze_translations(self, hours: int) -> Dict:
        """Analyze translation logs"""
        if not self.translations_log.exists():
            return {}
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        stats = {
            'total_requests': 0,
            'successful_translations': 0,
            'failed_translations': 0,
            'method_distribution': Counter(),
            'confidence_distribution': [],
            'processing_times': [],
            'user_feedback_count': 0,
            'positive_feedback': 0
        }
        
        try:
            with open(self.translations_log, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        entry_time = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                        
                        if entry_time < cutoff_time:
                            continue
                        
                        event_type = entry.get('event_type', '')
                        
                        if event_type == 'translation_request':
                            stats['total_requests'] += 1
                        elif event_type == 'translation_result':
                            if entry.get('success'):
                                stats['successful_translations'] += 1
                                stats['method_distribution'][entry.get('method', 'unknown')] += 1
                                if 'confidence' in entry:
                                    stats['confidence_distribution'].append(entry['confidence'])
                            else:
                                stats['failed_translations'] += 1
                            
                            if 'processing_time_ms' in entry:
                                stats['processing_times'].append(entry['processing_time_ms'])
                        
                        elif event_type == 'user_feedback':
                            stats['user_feedback_count'] += 1
                            if entry.get('is_positive'):
                                stats['positive_feedback'] += 1
                    
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
        
        except FileNotFoundError:
            pass
        
        return stats
    
    def _analyze_performance(self, hours: int) -> Dict:
        """Analyze performance logs"""
        if not self.performance_log.exists():
            return {}
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        stats = {
            'operations': Counter(),
            'avg_times': defaultdict(list),
            'slowest_operations': [],
            'fastest_operations': []
        }
        
        try:
            with open(self.performance_log, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        entry_time = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                        
                        if entry_time < cutoff_time:
                            continue
                        
                        if entry.get('event_type') == 'performance_metric':
                            operation = entry.get('operation', 'unknown')
                            duration = entry.get('duration_ms', 0)
                            
                            stats['operations'][operation] += 1
                            stats['avg_times'][operation].append(duration)
                            
                            # Track extremes
                            stats['slowest_operations'].append((operation, duration, entry_time))
                            stats['fastest_operations'].append((operation, duration, entry_time))
                    
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
        
        except FileNotFoundError:
            pass
        
        # Sort extremes
        stats['slowest_operations'].sort(key=lambda x: x[1], reverse=True)
        stats['fastest_operations'].sort(key=lambda x: x[1])
        
        return stats
    
    def _analyze_errors(self, hours: int) -> Dict:
        """Analyze error logs"""
        if not self.errors_log.exists():
            return {}
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        stats = {
            'total_errors': 0,
            'error_types': Counter(),
            'error_patterns': Counter(),
            'critical_errors': 0
        }
        
        try:
            with open(self.errors_log, 'r') as f:
                for line in f:
                    if 'ERROR' in line or 'CRITICAL' in line:
                        stats['total_errors'] += 1
                        
                        if 'CRITICAL' in line:
                            stats['critical_errors'] += 1
                        
                        # Simple error categorization
                        if 'database' in line.lower():
                            stats['error_types']['database'] += 1
                        elif 'translation' in line.lower():
                            stats['error_types']['translation'] += 1
                        elif 'api' in line.lower():
                            stats['error_types']['api'] += 1
                        else:
                            stats['error_types']['other'] += 1
        
        except FileNotFoundError:
            pass
        
        return stats
    
    def _print_translation_report(self, stats: Dict):
        """Print translation analytics"""
        print(f"\n{Colors.CYAN}{Colors.BOLD}🔤 TRANSLATION ANALYTICS{Colors.END}")
        print("-" * 40)
        
        total_requests = stats.get('total_requests', 0)
        successful = stats.get('successful_translations', 0)
        failed = stats.get('failed_translations', 0)
        
        success_rate = (successful / max(total_requests, 1)) * 100
        
        print(f"Total Requests: {Colors.BOLD}{total_requests}{Colors.END}")
        print(f"Successful: {Colors.GREEN}{successful}{Colors.END}")
        print(f"Failed: {Colors.RED}{failed}{Colors.END}")
        print(f"Success Rate: {Colors.BOLD}{success_rate:.1f}%{Colors.END}")
        
        # Method distribution
        if stats.get('method_distribution'):
            print(f"\n{Colors.YELLOW}Method Distribution:{Colors.END}")
            for method, count in stats['method_distribution'].most_common(5):
                percentage = (count / successful) * 100 if successful > 0 else 0
                print(f"  {method}: {count} ({percentage:.1f}%)")
        
        # Confidence stats
        if stats.get('confidence_distribution'):
            confidences = stats['confidence_distribution']
            avg_confidence = sum(confidences) / len(confidences)
            print(f"\nAvg Confidence: {Colors.BOLD}{avg_confidence:.2f}{Colors.END}")
        
        # User feedback
        feedback_count = stats.get('user_feedback_count', 0)
        positive_feedback = stats.get('positive_feedback', 0)
        if feedback_count > 0:
            feedback_rate = (positive_feedback / feedback_count) * 100
            print(f"User Feedback: {feedback_count} total, {positive_feedback} positive ({feedback_rate:.1f}%)")
    
    def _print_performance_report(self, stats: Dict):
        """Print performance analytics"""
        print(f"\n{Colors.MAGENTA}{Colors.BOLD}⚡ PERFORMANCE ANALYTICS{Colors.END}")
        print("-" * 40)
        
        if not stats.get('operations'):
            print("No performance data available")
            return
        
        print(f"Operations Tracked: {len(stats['operations'])}")
        print(f"Total Operations: {sum(stats['operations'].values())}")
        
        # Average times by operation
        print(f"\n{Colors.YELLOW}Average Processing Times:{Colors.END}")
        for operation, times in stats['avg_times'].items():
            if times:
                avg_time = sum(times) / len(times)
                print(f"  {operation}: {Colors.BOLD}{avg_time:.2f}ms{Colors.END}")
        
        # Slowest operations
        if stats.get('slowest_operations'):
            print(f"\n{Colors.RED}Slowest Operations (Top 3):{Colors.END}")
            for i, (op, duration, timestamp) in enumerate(stats['slowest_operations'][:3]):
                print(f"  {i+1}. {op}: {duration:.2f}ms")
    
    def _print_error_report(self, stats: Dict):
        """Print error analytics"""
        print(f"\n{Colors.RED}{Colors.BOLD}🚨 ERROR ANALYTICS{Colors.END}")
        print("-" * 40)
        
        total_errors = stats.get('total_errors', 0)
        critical_errors = stats.get('critical_errors', 0)
        
        print(f"Total Errors: {Colors.BOLD}{total_errors}{Colors.END}")
        print(f"Critical Errors: {Colors.RED}{critical_errors}{Colors.END}")
        
        if stats.get('error_types'):
            print(f"\n{Colors.YELLOW}Error Categories:{Colors.END}")
            for error_type, count in stats['error_types'].most_common():
                print(f"  {error_type}: {count}")
    
    def _print_health_summary(self, translation_stats: Dict, performance_stats: Dict, error_stats: Dict):
        """Print overall system health summary"""
        print(f"\n{Colors.GREEN}{Colors.BOLD}🏥 SYSTEM HEALTH SUMMARY{Colors.END}")
        print("=" * 40)
        
        # Overall health score
        success_rate = 0
        if translation_stats.get('total_requests', 0) > 0:
            success_rate = (translation_stats.get('successful_translations', 0) / translation_stats['total_requests']) * 100
        
        error_rate = error_stats.get('total_errors', 0)
        
        # Health determination
        if success_rate > 95 and error_rate < 10:
            health_status = f"{Colors.GREEN}EXCELLENT{Colors.END}"
        elif success_rate > 85 and error_rate < 25:
            health_status = f"{Colors.YELLOW}GOOD{Colors.END}"
        elif success_rate > 70:
            health_status = f"{Colors.YELLOW}FAIR{Colors.END}"
        else:
            health_status = f"{Colors.RED}NEEDS ATTENTION{Colors.END}"
        
        print(f"System Health: {Colors.BOLD}{health_status}{Colors.END}")
        print(f"Translation Success Rate: {success_rate:.1f}%")
        print(f"Error Count: {error_rate}")
        
        # Recommendations
        print(f"\n{Colors.BLUE}Recommendations:{Colors.END}")
        if success_rate < 90:
            print("  • Review translation methods and enhance dataset")
        if error_rate > 20:
            print("  • Investigate error patterns and improve error handling")
        if translation_stats.get('user_feedback_count', 0) > 0:
            print("  • User feedback available - consider dataset improvements")

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="WRAITH System Operational Tools")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Log tail command
    tail_parser = subparsers.add_parser('tail', help='Live log monitoring')
    tail_parser.add_argument('--type', choices=['all', 'main', 'translations', 'performance', 'errors'], 
                            default='all', help='Log type to monitor')
    tail_parser.add_argument('--filter', help='Filter events containing this string')
    
    # Analytics command
    analytics_parser = subparsers.add_parser('analytics', help='Generate system analytics report')
    analytics_parser.add_argument('--hours', type=int, default=24, help='Hours to analyze (default: 24)')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Quick system status check')
    
    args = parser.parse_args()
    
    if args.command == 'tail':
        tailer = LogTailer()
        tailer.tail_live(args.type, args.filter)
    
    elif args.command == 'analytics':
        analyzer = AnalyticsCLI()
        analyzer.generate_report(args.hours)
    
    elif args.command == 'status':
        analyzer = AnalyticsCLI()
        analyzer.generate_report(1)  # Quick 1-hour status
    
    else:
        print_banner()
        print(f"{Colors.YELLOW}Available commands:{Colors.END}")
        print("  tail       - Live log monitoring")
        print("  analytics  - System analytics report")  
        print("  status     - Quick status check")
        print(f"\nUse --help with any command for more options")

if __name__ == "__main__":
    main()