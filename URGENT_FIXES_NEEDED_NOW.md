# 🚨 URGENT FIXES NEEDED

## Discord Bot Crash Game Issues:

### 1. Use Animated GIFs (Not Static SVG) ✋
- Current: Generating static SVG frames
- Needed: Use actual animated GIF URLs
- **Betting:** Countdown timer GIF
- **Flying:** Rocket flying with smoke trail GIF  
- **Supersonic:** Fast rocket with orange glow GIF
- **Crashed:** Explosion GIF

### 2. Text Overlapping in Betting Phase
- Description text overlapping with countdown
- Need better spacing/formatting

### 3. Show Rocket on Graph with Trail
- Rocket should be ON the multiplier graph
- Show trailing path behind it as it climbs
- Not just a separate image

### 4. Bet List Display
- Should show bet list alongside the graph/GIF
- Not generated in the image

---

## Website Issues:

### 5. No Auto-Refresh - Needs Real-Time
- Currently requires manual refresh
- Should use Supabase real-time subscriptions
- Update multiplier/status automatically

### 6. Coinflip Animation Wrong
- One side purple (should be gold/silver)
- Resets after 3 seconds
- Should spin continuously until result
- Timing off

### 7. Roulette Wrong
- Not using the original wheel design
- Should use the previous roulette implementation

---

## Functional Issues:

### 8. Cashout Button Doesn't Work
- Button exists but doesn't execute cashout
- Needs debugging

---

## Priority Order:
1. Fix cashout button (critical)
2. Use GIFs instead of SVG for crash
3. Fix website real-time updates  
4. Fix coinflip animation
5. Restore original roulette
6. Add rocket to graph properly
7. Fix text overlap

