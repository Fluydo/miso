/**
 * Simple crash GIF generator using GIFEncoder
 * No Puppeteer, no ffmpeg - just pure Node.js
 */

const fs = require('fs');
const { createCanvas } = require('canvas');
const GIFEncoder = require('gifencoder');

const args = process.argv.slice(2);
if (args.length < 3) {
    console.error("Usage: node generate_crash_simple.js <phase> <multiplier> <output_path>");
    process.exit(1);
}

const [phase, multiplierStr, outputPath] = args;
const multiplier = parseFloat(multiplierStr);

const WIDTH = 700;
const HEIGHT = 400;
const FPS = 15;
const DURATION = 1; // 1 second
const FRAMES = FPS * DURATION;

// Phase configurations
const PHASE_CONFIG = {
    betting: {
        color: '#FEE75C',
        emoji: '🎰',
        text: 'BETTING'
    },
    running: {
        color: '#22C55E',
        emoji: '🚀',
        text: `${multiplier.toFixed(2)}x`
    },
    supersonic: {
        color: '#FF8C00',
        emoji: '🔥',
        text: `${multiplier.toFixed(2)}x`
    },
    crashed: {
        color: '#DC3232',
        emoji: '💥',
        text: `CRASHED ${multiplier.toFixed(2)}x`
    }
};

const config = PHASE_CONFIG[phase] || PHASE_CONFIG.running;

async function generateGIF() {
    const canvas = createCanvas(WIDTH, HEIGHT);
    const ctx = canvas.getContext('2d');
    
    const encoder = new GIFEncoder(WIDTH, HEIGHT);
    encoder.createReadStream().pipe(fs.createWriteStream(outputPath));
    
    encoder.start();
    encoder.setRepeat(0);   // Loop forever
    encoder.setDelay(1000 / FPS);  // Frame delay in ms
    encoder.setQuality(10); // Lower is better (1-20)
    
    // Generate frames
    for (let frame = 0; frame < FRAMES; frame++) {
        const progress = frame / (FRAMES - 1);
        
        // Clear with dark background
        ctx.fillStyle = '#1E1F23';
        ctx.fillRect(0, 0, WIDTH, HEIGHT);
        
        // Animated glow effect
        const glowSize = 200 + Math.sin(progress * Math.PI * 4) * 50;
        const gradient = ctx.createRadialGradient(WIDTH/2, HEIGHT/2, 0, WIDTH/2, HEIGHT/2, glowSize);
        gradient.addColorStop(0, config.color + '40');
        gradient.addColorStop(1, '#1E1F2300');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, WIDTH, HEIGHT);
        
        // Draw main text
        ctx.fillStyle = config.color;
        ctx.font = 'bold 100px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        // Pulse effect
        const scale = 1 + Math.sin(progress * Math.PI * 2) * 0.05;
        ctx.save();
        ctx.translate(WIDTH/2, HEIGHT/2);
        ctx.scale(scale, scale);
        ctx.fillText(config.text, 0, 0);
        ctx.restore();
        
        // Draw phase indicator
        ctx.font = 'bold 32px Arial';
        ctx.fillStyle = '#FFFFFF80';
        ctx.fillText(config.emoji + ' ' + phase.toUpperCase(), WIDTH/2, HEIGHT - 50);
        
        encoder.addFrame(ctx);
    }
    
    encoder.finish();
    console.log(`✅ Generated: ${outputPath}`);
}

generateGIF().catch(err => {
    console.error('❌ Error:', err);
    process.exit(1);
});
