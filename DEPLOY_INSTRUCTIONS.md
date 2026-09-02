# Deploy Instructions

## Files for OLD PC Only

These files should ONLY be used on the OLD PC that runs the bot:

### 1. **crash_NEW.py**
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

### 2. **main_RESTART.py**
- This is a dummy file to trigger restarts
- **How to use from this PC:**
  1. Edit `main_RESTART.py` and change the restart number (e.g., `# 1` → `# 2`)
  2. Commit: `git add main_RESTART.py && git commit -m "trigger restart"`
  3. Push: `git push origin main`
  4. Old PC will detect the new commit and restart the bot

**Why?** This lets you restart the old PC bot without modifying the actual bot code on this PC.

## Deployment Checklist for OLD PC

When you go to the old PC, do these steps:

1. **Pull latest changes:**
   ```bash
   cd "path/to/Miso Bot"
   git pull origin main
   ```

2. **Backup and rename crash.py:**
   ```bash
   cd cogs
   mv crash.py crash_OLD_BACKUP.py
   mv crash_NEW.py crash.py
   cd ..
   ```

3. **Restart the bot:**
   ```bash
   python main.py
   ```

4. **On first startup:**
   - Bot will detect missing puppeteer
   - Will run `npm install` automatically (takes 5-10 minutes first time)
   - Bot will then start normally

5. **Verify:**
   - Check Discord - crash game should show bets in the description
   - GIFs should be HTML-rendered (not just text)

## Emergency: Revert Changes

If something breaks on old PC:

```bash
cd cogs
mv crash.py crash_BROKEN.py
mv crash_OLD_BACKUP.py crash.py
cd ..
python main.py
```

## Current Status

- ✅ Website: Shows user avatars and usernames
- ✅ Website: Betting works
- ✅ Website: Graph doesn't freeze
- ⏳ Bot: Needs deployment to old PC for new features
  - HTML-rendered GIFs (via Puppeteer)
  - Bets list in description (not separate image)
  - Auto npm install on startup
