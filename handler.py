#!/usr/bin/env python3
"""
Miso Bot Auto-Update Handler
Monitors GitHub for updates and auto-restarts the bot.
"""
import os
import sys
import time
import subprocess
import signal
import asyncio
from pathlib import Path

# Configuration
CHECK_INTERVAL = 30  # Check for updates every 30 seconds
RESTART_DELAY = 3    # Wait 3 seconds before restarting after update

class BotHandler:
    def __init__(self):
        self.bot_process = None
        self.script_dir = Path(__file__).parent
        self.running = True
        
    def log(self, message):
        """Print with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def kill_all_python_processes(self):
        """Kill all Python processes except this handler"""
        self.log("Stopping all bot processes...")
        current_pid = os.getpid()
        
        try:
            # Windows
            if sys.platform == "win32":
                # Get all python processes
                result = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
                    capture_output=True,
                    text=True
                )
                
                # Kill each python process except this one
                for line in result.stdout.split('\n'):
                    if 'python.exe' in line.lower():
                        try:
                            parts = line.split(',')
                            if len(parts) >= 2:
                                pid = int(parts[1].strip('"'))
                                if pid != current_pid:
                                    subprocess.run(["taskkill", "/F", "/PID", str(pid)], 
                                                 capture_output=True)
                        except:
                            pass
            else:
                # Unix-like
                subprocess.run(["pkill", "-9", "python"], capture_output=True)
                
            time.sleep(2)  # Wait for processes to die
            self.log("All bot processes stopped.")
            
        except Exception as e:
            self.log(f"Warning: Could not kill all processes: {e}")
            
    def clean_cache(self):
        """Remove Python cache files"""
        self.log("Cleaning Python cache...")
        try:
            for root, dirs, files in os.walk(self.script_dir):
                # Remove __pycache__ directories
                if '__pycache__' in dirs:
                    cache_dir = Path(root) / '__pycache__'
                    try:
                        for file in cache_dir.glob('*.pyc'):
                            file.unlink()
                        cache_dir.rmdir()
                    except:
                        pass
                        
                # Remove .pyc files
                for file in files:
                    if file.endswith('.pyc'):
                        try:
                            (Path(root) / file).unlink()
                        except:
                            pass
                            
            self.log("Cache cleaned.")
        except Exception as e:
            self.log(f"Warning: Cache cleaning failed: {e}")
            
    def check_for_updates(self):
        """Check if there are updates on GitHub"""
        try:
            # Fetch latest from origin
            result = subprocess.run(
                ["git", "fetch", "origin", "main"],
                cwd=self.script_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                # Fetch failed, but don't crash
                return False
                
            # Check if local is behind remote
            result = subprocess.run(
                ["git", "rev-list", "HEAD...origin/main", "--count"],
                cwd=self.script_dir,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                commits_behind = int(result.stdout.strip())
                return commits_behind > 0
                
            return False
            
        except Exception as e:
            # Don't crash on git errors
            return False
            
    def pull_updates(self):
        """Pull latest code from GitHub"""
        self.log("📥 Pulling latest code from GitHub...")
        
        try:
            # Stash local changes to data files
            subprocess.run(
                ["git", "stash", "push", "-u", "--", "data/*.json"],
                cwd=self.script_dir,
                capture_output=True,
                timeout=10
            )
            
            # Pull latest code
            result = subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=self.script_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                # Pull failed, try reset
                self.log("⚠️  Pull failed, trying reset...")
                subprocess.run(
                    ["git", "reset", "--hard", "origin/main"],
                    cwd=self.script_dir,
                    timeout=10
                )
                
            # Restore stashed data files
            subprocess.run(
                ["git", "stash", "pop"],
                cwd=self.script_dir,
                capture_output=True,
                timeout=10
            )
            
            self.log("✅ Code updated successfully!")
            return True
            
        except Exception as e:
            self.log(f"❌ Update failed: {e}")
            return False
            
    def start_bot(self):
        """Start the bot process"""
        self.log("🤖 Starting Miso Bot...")
        
        try:
            # Start bot as subprocess
            self.bot_process = subprocess.Popen(
                [sys.executable, "main.py"],
                cwd=self.script_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            self.log(f"✅ Bot started (PID: {self.bot_process.pid})")
            return True
            
        except Exception as e:
            self.log(f"❌ Failed to start bot: {e}")
            return False
            
    def monitor_bot(self):
        """Monitor bot output and check for crashes"""
        if not self.bot_process:
            return False
            
        try:
            # Check if process is still running
            if self.bot_process.poll() is not None:
                self.log("⚠️  Bot process died!")
                return False
                
            # Read and print bot output (non-blocking)
            if self.bot_process.stdout:
                try:
                    line = self.bot_process.stdout.readline()
                    if line:
                        print(line, end='')
                except:
                    pass
                    
            return True
            
        except:
            return False
            
    def stop_bot(self):
        """Stop the bot gracefully"""
        if self.bot_process:
            self.log("Stopping bot...")
            try:
                self.bot_process.terminate()
                self.bot_process.wait(timeout=5)
            except:
                self.bot_process.kill()
                
            self.bot_process = None
            
    def run(self):
        """Main handler loop"""
        print("\n" + "="*50)
        print("   MISO BOT AUTO-UPDATE HANDLER")
        print("="*50)
        print(f"Checking for updates every {CHECK_INTERVAL} seconds")
        print("Press Ctrl+C to stop")
        print("="*50 + "\n")
        
        # Initial setup
        self.kill_all_python_processes()
        self.clean_cache()
        
        # Start bot
        if not self.start_bot():
            self.log("Failed to start bot. Exiting.")
            return
            
        last_check = 0
        
        try:
            while self.running:
                # Monitor bot
                if not self.monitor_bot():
                    self.log("⚠️  Bot crashed! Restarting in 5 seconds...")
                    time.sleep(5)
                    self.clean_cache()
                    self.start_bot()
                    last_check = time.time()
                    continue
                    
                # Check for updates periodically
                current_time = time.time()
                if current_time - last_check >= CHECK_INTERVAL:
                    last_check = current_time
                    
                    if self.check_for_updates():
                        self.log("🔔 Updates available!")
                        
                        # Stop bot
                        self.stop_bot()
                        time.sleep(1)
                        
                        # Pull updates
                        if self.pull_updates():
                            self.clean_cache()
                            self.log(f"Restarting bot in {RESTART_DELAY} seconds...")
                            time.sleep(RESTART_DELAY)
                            self.start_bot()
                        else:
                            self.log("Update failed. Restarting bot anyway...")
                            time.sleep(RESTART_DELAY)
                            self.start_bot()
                            
                # Small sleep to prevent CPU spinning
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            self.log("\n🛑 Shutting down...")
            self.stop_bot()
            self.log("Goodbye!")
            
        except Exception as e:
            self.log(f"❌ Handler error: {e}")
            self.stop_bot()
            

if __name__ == "__main__":
    handler = BotHandler()
    handler.run()
