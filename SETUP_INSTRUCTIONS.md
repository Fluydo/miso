# Crash Game GIF Setup Instructions

## Step 1: Install GIF Dependencies

Run this file by double-clicking it:
```
TEST_GIF.bat
```

This will:
- Install `gifencoder` and `canvas` packages
- Test all 4 GIF phases (betting, running, supersonic, crashed)
- Create test GIF files you can view

## Step 2: Restart the Bot

1. Stop the bot (CTRL+C in the terminal)
2. Start it again: `python main.py`

## Step 3: Delete Old Message & Setup New One

The old message has an embed format. You need to create a fresh one:

1. In Discord, delete the old crash game message (or just run `/crashsetup` in a new channel)
2. Run: `/crashsetup #channel-name`
3. The new message will use Component v2 format (content + GIF + buttons, NO embed)

## What Was Fixed

### GIF Generation
- **OLD**: Used Puppeteer + ffmpeg (requires complex setup, was timing out)
- **NEW**: Uses `gifencoder` + `canvas` (pure Node.js, no external dependencies)
- GIFs are now animated with glow and pulse effects
- 1 second duration, 15 FPS, smooth animation

### Message Format
- **OLD**: Had embed with blue box
- **NEW**: Pure Component v2 - content text + GIF attachment + buttons only
- The code was already correct, just need to delete old message

### Files Changed
1. `generate_crash_simple.js` - NEW simple GIF generator
2. `functions/renderer.py` - Updated to use new script
3. `package.json` - Added gifencoder and canvas dependencies
4. `TEST_GIF.bat` - Easy testing script

## Troubleshooting

### If GIFs still don't work:
1. Check if test GIFs were created successfully
2. Look at bot logs for `[GIF] Generated:` messages
3. If you see `[GIF] Node.js timed out`, the dependencies didn't install properly

### If message still shows embed:
- You're looking at the OLD message
- Delete it and run `/crashsetup` again
- Or use a fresh channel

## Testing

After setup, the live message should show:
```
🎰 BETTING PHASE
Starting in 8 seconds — Place your bets now!

[ANIMATED GIF HERE]

Current Bets (0)
No bets yet
Play on the website for a better experience

[🎰 Place Bet] [💰 Cash Out]
```

NO blue embed box should appear!
