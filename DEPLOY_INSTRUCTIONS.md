# Deploy Instructions

## 🛑 How to STOP the Old PC Bot (From This PC)

Just run `STOP.bat` - it will:
1. Update STOP_SIGNAL.txt
2. Commit and push to GitHub
3. Old PC bot detects the signal within 10 seconds and shuts down

**Or manually:**
```bash
git add STOP_SIGNAL.txt
git commit -m "STOP: shut down old PC bot"
git push origin main
```

## 🔄 How to RESTART the Old PC Bot (From This PC)

Edit `main_RESTART.py` and change the restart number, then:
```bash
git add main_RESTART.py
git commit -m "restart old pc bot"
git push origin main
```

Old PC will detect the change and restart automatically.

## Files for OLD PC Only

These files should ONLY be used/renamed on the OLD PC:

### 1. **main_WITH_STOP_CHECK.py**
- Main.py with STOP signal detection
- **ON OLD PC:** Rename `main.py` to `main_OLD_BACKUP.py`
- **ON OLD PC:** Rename `main_WITH_STOP_CHECK.py` to `main.py`
- **DO NOT** rename on this PC!

**What it does:**
- Checks STOP_SIGNAL.txt every 10 seconds
- Shuts down gracefully when STOP signal detected
- Same as regular main.py otherwise

### 2. **crash_NEW.py**
- This is the new crash game cog with ComponentV2 layout
- **ON OLD PC:** Rename `cogs/crash.py` to `cogs/crash_OLD_BACKUP.py`
- **ON OLD PC:** Rename `cogs/crash_NEW.py` to `cogs/crash.py`
- **DO NOT** rename on this PC!

**What's new:**
- Bets list is embedded directly in the Discord message description
- No more separate bets image message
- Cleaner, single-message layout
- Shows up to 10 bets with user mentions
- Shows who cashed out and at what multiplier

## Deployment Checklist for OLD PC

When you go to the old PC, do these steps:

1. **Pull latest changes:**
   ```bash
   cd "path/to/Miso Bot"
   git pull origin main
   ```

2. **Backup and rename main.py:**
   ```bash
   mv main.py main_OLD_BACKUP.py
   mv main_WITH_STOP_CHECK.py main.py
   ```

3. **Backup and rename crash.py:**
   ```bash
   cd cogs
   mv crash.py crash_OLD_BACKUP.py
   mv crash_NEW.py crash.py
   cd ..
   ```

4. **Restart the bot:**
   ```bash
   python main.py
   ```

5. **On first startup:**
   - Bot will detect missing puppeteer
   - Will run `npm install` automatically (takes 5-10 minutes first time)
   - Bot will then start normally
   - STOP signal checker will be active (checks every 10s)

6. **Verify:**
   - Check Discord - crash game should show bets in the description
   - GIFs should be HTML-rendered (not just text)
   - Check logs for "STOP signal monitoring ENABLED"

## Testing on This PC (Before Going to Old PC)

You can test the new code locally without affecting the old PC:

1. **Stop old PC bot first:**
   ```bash
   # Run STOP.bat or manually:
   git add STOP_SIGNAL.txt
   git commit -m "STOP old pc"
   git push origin main
   ```

2. **Wait 10 seconds** for old PC to detect and stop

3. **Test locally on this PC:**
   ```bash
   # Backup your current main.py
   cp main.py main_LOCAL_BACKUP.py
   
   # Use the new version
   cp main_WITH_STOP_CHECK.py main.py
   
   # Test
   python main.py
   ```

4. **When done testing, restore:**
   ```bash
   cp main_LOCAL_BACKUP.py main.py
   ```

5. **Remove STOP signal to restart old PC:**
   ```bash
   # Edit STOP_SIGNAL.txt and remove "STOP" line or delete the file
   git add STOP_SIGNAL.txt
   git commit -m "resume old pc"
   git push origin main
   ```

## Emergency: Revert Changes

If something breaks on old PC:

```bash
# Revert main.py
mv main.py main_BROKEN.py
mv main_OLD_BACKUP.py main.py

# Revert crash.py
cd cogs
mv crash.py crash_BROKEN.py
mv crash_OLD_BACKUP.py crash.py
cd ..

# Restart
python main.py
```

## Current Status

- ✅ Website: Shows user avatars and usernames
- ✅ Website: Betting works
- ✅ Website: Graph doesn't freeze
- ✅ STOP.bat: Remote shutdown capability
- ⏳ Bot: Needs deployment to old PC for new features
  - HTML-rendered GIFs (via Puppeteer)
  - Bets list in description (not separate image)
  - Auto npm install on startup
  - STOP signal monitoring
