#!/usr/bin/env python3
"""
YouTube Clip Pipeline Monitor
Simple script to check pipeline status and show recent logs
"""

import os
import sys
import subprocess
import time
from datetime import datetime

def check_pipeline_status():
    """Check if the pipeline is running"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "youtube_clip_pipeline.py"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0, result.stdout.strip()
    except:
        return False, ""

def get_recent_logs(lines=20):
    """Get recent log entries"""
    log_file = "logs/youtube_pipeline.log"
    if os.path.exists(log_file):
        try:
            result = subprocess.run(
                ["tail", "-n", str(lines), log_file],
                capture_output=True,
                text=True
            )
            return result.stdout
        except:
            return "Error reading logs"
    return "Log file not found"

def get_system_stats():
    """Get basic system statistics"""
    try:
        # Get disk usage
        disk_result = subprocess.run(
            ["df", "-h", "."],
            capture_output=True,
            text=True
        )
        disk_info = disk_result.stdout.split('\n')[1].split()
        disk_free = disk_info[3] if len(disk_info) > 3 else "Unknown"
        
        # Get memory usage
        mem_result = subprocess.run(
            ["free", "-h"],
            capture_output=True,
            text=True
        )
        mem_lines = mem_result.stdout.split('\n')
        mem_info = mem_lines[1].split() if len(mem_lines) > 1 else []
        mem_free = mem_info[6] if len(mem_info) > 6 else "Unknown"
        
        return f"Disk Free: {disk_free}, Memory Available: {mem_free}"
    except:
        return "Unable to get system stats"

def count_files_in_dirs():
    """Count files in pipeline directories"""
    stats = {}
    dirs = ["downloads", "clips", "finished_clips"]
    
    for dir_name in dirs:
        if os.path.exists(dir_name):
            files = [f for f in os.listdir(dir_name) if os.path.isfile(os.path.join(dir_name, f))]
            stats[dir_name] = len(files)
        else:
            stats[dir_name] = 0
            
    return stats

def main():
    """Main monitoring function"""
    print("🎬 YouTube Clip Pipeline Monitor")
    print("=" * 50)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check pipeline status
    is_running, pid = check_pipeline_status()
    if is_running:
        print(f"✅ Pipeline is RUNNING (PID: {pid})")
    else:
        print("❌ Pipeline is NOT RUNNING")
    
    print()
    
    # System stats
    print("📊 System Status:")
    print(f"   {get_system_stats()}")
    print()
    
    # File counts
    print("📁 File Counts:")
    file_counts = count_files_in_dirs()
    for dir_name, count in file_counts.items():
        print(f"   {dir_name}: {count} files")
    print()
    
    # Recent logs
    print("📋 Recent Logs (last 10 lines):")
    print("-" * 30)
    logs = get_recent_logs(10)
    print(logs)
    print("-" * 30)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--watch":
        print("\n👁️  Watching logs (Ctrl+C to stop)...")
        try:
            subprocess.run(["tail", "-f", "logs/youtube_pipeline.log"])
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped")

if __name__ == "__main__":
    main()