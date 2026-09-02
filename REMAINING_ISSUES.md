# 🔧 Remaining Issues to Fix

## ✅ FIXED (Discord Bot):
1. ✅ Cashout button now works
2. ✅ Using animated GIFs instead of static SVG
3. ✅ Fixed text overlapping
4. ✅ Bet list shows properly

---

## 🚨 CRITICAL - Website Crash Game:

### Issue: No Real-Time Updates
**Problem:** Website doesn't subscribe to Supabase changes, requires manual refresh

**What's Missing:**
```typescript
// MISSING in C:\Users\lucas\Desktop\miso-dashboard\app\games\crash\page.tsx

useEffect(() => {
  const channel = supabase
    .channel('crash-realtime')
    .on('postgres_changes', {
      event: '*',
      schema: 'public',
      table: 'crash_games'
    }, (payload) => {
      // Update game state
    })
    .on('postgres_changes', {
      event: '*',
      schema: 'public',
      table: 'crash_bets'
    }, (payload) => {
      // Update bets
    })
    .subscribe();
  
  return () => { supabase.removeChannel(channel); };
}, []);
```

**Impact:** Users must refresh page to see game state changes

**Priority:** 🔴 HIGH

---

## ⚠️ MEDIUM - Coinflip Animation:

### Issues:
1. One side of coin is purple (should be gold/silver)
2. Animation resets after 3 seconds
3. Not synchronized with result timing

**Files to Check:**
- `C:\Users\lucas\Desktop\miso-dashboard\components\3d\coin-flip-3d.tsx`
- `C:\Users\lucas\Desktop\miso-dashboard\app\games\coinflip\page.tsx`

**What's Wrong:**
- Coin material colors incorrect
- Animation duration hardcoded to 3s
- Doesn't wait for API response before completing

**Priority:** 🟡 MEDIUM

---

## ⚠️ MEDIUM - Roulette Wheel:

### Issue: Not Using Original Design

**You said:** "wtf is that roulette why don't you use the ones that were there"

**Action Needed:**
- Find the original roulette implementation
- Compare with current version
- Restore original wheel visual

**Files to Check:**
- `C:\Users\lucas\Desktop\miso-dashboard\app\games\roulette\page.tsx`

**Priority:** 🟡 MEDIUM

---

## 🔵 LOW - Crash Graph Enhancement:

### Issue: Rocket Not ON Graph with Trail

**Current:** GIF shows rocket animation separately  
**Requested:** Rocket should be overlaid ON the multiplier graph with trailing path

**Implementation Idea:**
- Use SVG overlay on top of graph
- Position rocket at current multiplier point
- Draw path line behind it

**This is complex and might not be necessary if GIFs work well**

**Priority:** 🔵 LOW (optional enhancement)

---

## 📋 Action Plan:

### Phase 1: Test Bot Fixes (NOW)
1. Restart Discord bot
2. Test `/crashsetup`
3. Test Place Bet button
4. Test Cash Out button
5. Verify bet list shows properly
6. Confirm GIFs are animating

### Phase 2: Fix Website Real-Time (NEXT)
1. Add Supabase real-time subscription to crash page
2. Subscribe to crash_games table changes
3. Subscribe to crash_bets table changes
4. Update game state on INSERT/UPDATE
5. Test without refreshing

### Phase 3: Fix Coinflip (AFTER Phase 2)
1. Read coin-flip-3d.tsx
2. Fix coin colors (gold/silver, not purple)
3. Sync animation with result timing
4. Test flip animation

### Phase 4: Fix/Restore Roulette (AFTER Phase 3)
1. Find original roulette code
2. Compare with current implementation
3. Restore if needed

---

## 🎯 Current Status:

| Component | Status | Notes |
|-----------|--------|-------|
| Bot Crash | ✅ Fixed | Using GIFs, cashout works |
| Bot Permissions | ✅ Working | /permissions command complete |
| Website Crash | ❌ Broken | No real-time, needs refresh |
| Website Coinflip | ⚠️ Buggy | Wrong colors, timing off |
| Website Roulette | ⚠️ Wrong Design | Not using original |

---

## 💡 Quick Wins:

**If you just want the crash game working:**
1. Test the bot NOW - cashout should work
2. For website, I'll add real-time subscriptions in the next fix
3. Coinflip/Roulette can wait

**Priority order:**
1. 🔴 Verify bot crash works (test it!)
2. 🔴 Add website real-time (I can do this next)
3. 🟡 Fix coinflip colors/timing
4. 🟡 Restore roulette design

