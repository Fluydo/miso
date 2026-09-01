# 🤖 Old PC - Zero-Touch Setup

## One-Time Setup (Run Once on Old PC)

### Step 1: Run This (As Administrator)
Right-click PowerShell → Run as Administrator, then:
```powershell
cd "C:\path\to\Miso Bot"
Set-ExecutionPolicy Bypass -Scope Process -Force
.\setup-autostart.ps1
```

**That's it!** You never need to touch the old PC again.

---

## ✅ What This Does:

### Automatic Features:
1. **Boot Auto-Start** - Bot starts when Windows boots
2. **Auto-Update** - Checks GitHub every 5 minutes
3. **Auto-Restart** - Restarts if bot crashes
4. **Conflict Handling** - Stashes local changes before pulling
5. **Cache Cleanup** - Removes .pyc files automatically

### What Happens When You Push Code:
1. Old PC checks GitHub every 5 minutes
2. Detects new commits
3. Stops bot gracefully
4. Pulls latest code (no conflicts)
5. Installs new dependencies if needed
6. Restarts bot automatically

**Time from push to old PC updated**: ~5 minutes max

---

## 🎯 How It Works:

### Files Created:
- `auto-update.bat` - Checks for updates every 5 minutes
- `start-persistent.bat` - Keeps bot running, auto-restarts on crash
- `setup-autostart.ps1` - Sets up Windows Task Scheduler
- `pull.bat` - Manual pull with conflict handling (backup option)

### Scheduled Task:
- **Name**: MisoBot-AutoStart
- **Trigger**: System startup
- **Action**: Run start-persistent.bat
- **Permissions**: SYSTEM (highest)
- **Restart**: 3 attempts if crashes

---

## 📋 Manual Options (If Needed):

### Start Bot Manually:
```
Double-click: start-persistent.bat
```

### Pull Updates Manually:
```
Double-click: pull.bat
```

### Stop Auto-Start:
```powershell
schtasks /delete /tn "MisoBot-AutoStart" /f
```

### Check Task Status:
```powershell
Get-ScheduledTask -TaskName "MisoBot-AutoStart"
```

---

## 🐛 Troubleshooting:

### Bot Not Starting on Boot?
1. Check if task exists: `schtasks /query /tn "MisoBot-AutoStart"`
2. Re-run: `setup-autostart.ps1`
3. Check bot path is correct

### Updates Not Pulling?
1. Check internet connection
2. Verify GitHub credentials work
3. Check auto-update.bat is running (Task Manager → cmd.exe)

### Bot Keeps Crashing?
1. Check main.py console for errors
2. Verify Python is installed
3. Run: `pip install -r requirements.txt`

---

## 🎮 Current Configuration:

### Update Check Interval:
- **Current**: Every 5 minutes
- **To Change**: Edit `timeout /t 300` in auto-update.bat (300 = 5 minutes)

### Restart on Crash:
- **Current**: 3 attempts, 1 minute apart
- **To Change**: Edit `-RestartCount 3 -RestartInterval` in setup-autostart.ps1

---

## ✅ Verification:

After running setup, verify:
1. Task Scheduler shows "MisoBot-AutoStart" task
2. Bot starts automatically after reboot
3. Console shows update checks every 5 minutes
4. Push a change, wait 5 minutes, verify bot updates

---

## 🔒 Security Note:

The task runs as SYSTEM account with highest privileges. This is required for:
- Starting on boot without user login
- Killing/restarting Python processes
- Installing pip dependencies

If this is a security concern, change `$principal` in setup-autostart.ps1 to use your user account.

---

**Status**: Ready for one-time setup on old PC
**After Setup**: Zero maintenance required!
