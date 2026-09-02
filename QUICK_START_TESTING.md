# 🚀 QUICK START - Test Everything NOW

## Step 1: Install Requirements

```powershell
pip install Pillow supabase
```

or double-click:
- `install-supabase.bat`

---

## Step 2: Restart Bot

```powershell
python main.py
```

**Watch for:**
```
[INFO] Loaded extension: cogs.crash
[INFO] Loaded extension: cogs.levels
[INFO] Loaded extension: cogs.permissions
```

---

## Step 3: Test Crash Game

In Discord:
```
/crashsetup #crash-channel
```

**You should see:**
- Animated countdown circle (betting phase)
- Rocket climbing with trail (running phase)
- Orange supersonic rocket (5x+)
- Explosion animation (crashed)
- **NEW GIF every 2 seconds!**

Try:
```
/crashbet 50
```
Click "Cash Out" button during game!

---

## Step 4: Test Leveling

Send messages in any channel to gain XP!

Check your level:
```
/rank
```

Give yourself XP to test:
```
/level xp give @yourself 5000
```

**You should reach Level ~8-9 with 5000 XP!**

Check server roles - should see:
- Level 5 (dark green)
- Level 10 (cyan)
- Level 15 (light blue)
- Level 20 (blue)

If your server has 14+ boosts:
- Roles will have gradients
- Roles will have custom icons

---

## Step 5: Test Permissions (Optional)

```
/permissions
```

- Select a category
- Select a command
- Set whitelist/blacklist mode
- Add channel restrictions
- Add role/user exclusions

---

## 🎯 What to Expect:

### Crash Game:
- ✅ Smooth animated GIF (not external URLs)
- ✅ Updates every 2 seconds
- ✅ Bet list shows below GIF
- ✅ Buttons work (Place Bet, Cash Out)

### Leveling:
- ✅ Much faster progression
- ✅ Level 10 at ~3,600 XP (was 10,500)
- ✅ Roles auto-created
- ✅ Correct colors (green, cyan, light blue, blue)
- ✅ Gradients + icons if boosted server

### Permissions:
- ✅ Interactive panel
- ✅ Whitelist/blacklist modes
- ✅ Role/user exclusions
- ✅ Per-command or per-category

---

## ⚠️ Troubleshooting:

**GIF not showing?**
- Make sure Pillow is installed: `pip install Pillow`
- Check bot has permission to attach files

**Roles not created?**
- Bot needs "Manage Roles" permission
- Send a message to trigger XP gain

**Icons not showing?**
- Server needs 14+ boosts (Tier 2)
- Emojis must exist in server or shared servers

**Cashout button not working?**
- Make sure you placed a bet first
- Game must be in "running" phase
- Check console for errors

---

## 📝 Files Changed:

- `functions/renderer.py` - Added GIF generator
- `cogs/crash.py` - Uses generated GIFs
- `functions/levels.py` - New XP formula + colors
- `cogs/levels.py` - Gradient + icon support
- `cogs/permissions.py` - Full system (already done)

---

## 🎉 Everything Ready!

All systems are GO. Test the crash game and leveling now!

If you find issues, check console for error messages.
