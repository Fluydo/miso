# Emoji API Integration Guide

## Overview
The dashboard can now fetch emojis from three sources:
1. **Unicode Emojis** - Standard emojis like 😭, 💀, 🔥 (from GitHub API)
2. **Server Emojis** - Custom emojis from the current server (from Supabase)
3. **Bot Emojis** - All custom emojis from servers the bot is in (from Supabase)

## Setup

### 1. Run the SQL Migration
Run the SQL in `RUN_THIS_SQL.sql` on your Supabase dashboard to create:
- `server_emojis` table - stores emojis per guild
- `bot_emojis` table - stores all bot emojis

### 2. Restart the Bot
The bot will automatically sync emojis to Supabase:
- On startup
- Every hour (automatic sync)

## Frontend Implementation

### 1. Fetch Unicode Emojis (GitHub API)
```javascript
// Fetch all Unicode emojis from GitHub
const response = await fetch('https://api.github.com/emojis');
const unicodeEmojis = await response.json();

// Response format:
// {
//   "sob": "https://github.githubassets.com/images/icons/emoji/unicode/1f62d.png?v8",
//   "skull": "https://github.githubassets.com/images/icons/emoji/unicode/1f480.png?v8",
//   ...
// }

// Convert to your format:
const unicodeList = Object.entries(unicodeEmojis).map(([shortcode, url]) => ({
  shortcode: shortcode,
  url: url,
  type: 'unicode'
}));
```

### 2. Fetch Server Emojis (Supabase)
```javascript
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// Get server-specific emojis
const { data: serverEmojis } = await supabase
  .from('server_emojis')
  .select('*')
  .eq('guild_id', currentGuildId);

// Response format:
// [
//   {
//     guild_id: "1543920075097251850",
//     emoji_id: "123456789",
//     emoji_name: "custom_emoji",
//     emoji_animated: false,
//     emoji_url: "https://cdn.discordapp.com/emojis/123456789.png"
//   }
// ]
```

### 3. Fetch Bot Emojis (Supabase)
```javascript
// Get all bot emojis (from all servers)
const { data: botEmojis } = await supabase
  .from('bot_emojis')
  .select('*');

// Response format: same as server_emojis
```

### 4. Complete Integration Example
```javascript
async function fetchAllEmojis(guildId) {
  // 1. Fetch Unicode emojis
  const unicodeResponse = await fetch('https://api.github.com/emojis');
  const githubEmojis = await unicodeResponse.json();
  
  const unicodeEmojis = Object.entries(githubEmojis).map(([shortcode, url]) => ({
    id: shortcode,
    name: shortcode,
    url: url,
    type: 'unicode',
    animated: false
  }));

  // 2. Fetch server emojis
  const { data: serverEmojis } = await supabase
    .from('server_emojis')
    .select('*')
    .eq('guild_id', guildId);

  const formattedServerEmojis = serverEmojis.map(e => ({
    id: e.emoji_id,
    name: e.emoji_name,
    url: e.emoji_url,
    type: 'server',
    animated: e.emoji_animated
  }));

  // 3. Fetch bot emojis
  const { data: botEmojis } = await supabase
    .from('bot_emojis')
    .select('*');

  const formattedBotEmojis = botEmojis.map(e => ({
    id: e.emoji_id,
    name: e.emoji_name,
    url: e.emoji_url,
    type: 'bot',
    animated: e.emoji_animated
  }));

  return {
    unicode: unicodeEmojis,
    server: formattedServerEmojis,
    bot: formattedBotEmojis
  };
}
```

## Usage in Mention Editor

### Display in Tooltip
```javascript
const emojis = await fetchAllEmojis(currentGuildId);
const allEmojis = [
  ...emojis.unicode,
  ...emojis.server,
  ...emojis.bot
];

// Filter by search query
const filtered = allEmojis.filter(e => 
  e.name.toLowerCase().includes(searchQuery.toLowerCase())
);

// Render in tooltip
filtered.forEach(emoji => {
  console.log(`${emoji.name}: ${emoji.url}`);
});
```

### Convert in Preview/Editor
```javascript
// Convert :shortcode: to actual emoji in preview
function convertEmojis(text) {
  // Replace Unicode emojis
  const unicodeMap = new Map(emojis.unicode.map(e => [e.name, e.url]));
  text = text.replace(/:(\w+):/g, (match, shortcode) => {
    const emoji = unicodeMap.get(shortcode);
    return emoji ? `<img src="${emoji}" alt=":${shortcode}:" class="emoji">` : match;
  });

  // Replace custom emojis
  const customMap = new Map([
    ...emojis.server.map(e => [e.name, e.url]),
    ...emojis.bot.map(e => [e.name, e.url])
  ]);
  
  text = text.replace(/<:([\w]+):(\d+)>/g, (match, name, id) => {
    const emoji = customMap.get(name);
    return emoji ? `<img src="${emoji}" alt=":${name}:" class="emoji">` : match;
  });

  return text;
}
```

## Benefits
✅ No local server needed - everything is cloud-based
✅ Unicode emojis from GitHub's free API (no rate limits for reasonable use)
✅ Custom emojis synced automatically from Discord to Supabase
✅ Real-time updates via Supabase (emojis sync every hour)
✅ Works from anywhere, not just localhost

## Notes
- GitHub API has rate limits (~60 requests/hour unauthenticated)
- Cache the Unicode emoji list in localStorage/memory
- Bot syncs emojis automatically every hour
- Manual sync: restart the bot
