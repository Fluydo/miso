/**
 * Pure JavaScript crash GIF generator
 * Uses omggif - no native dependencies, no canvas, pure JS
 */

const fs = require('fs');
const GifEncoder = require('omggif').GifWriter;

const args = process.argv.slice(2);
if (args.length < 3) {
    console.error("Usage: node generate_crash_pure.js <phase> <multiplier> <output_path>");
    process.exit(1);
}

const [phase, multiplierStr, outputPath] = args;
const multiplier = parseFloat(multiplierStr);

const WIDTH = 700;
const HEIGHT = 400;
const FPS = 10;
const DURATION = 1; // 1 second
const FRAMES = FPS * DURATION;

// Phase configurations
const PHASE_CONFIG = {
    betting: {
        bg: [254, 231, 92],    // Yellow
        text: 'BETTING',
        emoji: '🎰'
    },
    running: {
        bg: [34, 197, 94],     // Green
        text: `${multiplier.toFixed(2)}x`,
        emoji: '🚀'
    },
    supersonic: {
        bg: [255, 140, 0],     // Orange
        text: `${multiplier.toFixed(2)}x`,
        emoji: '🔥'
    },
    crashed: {
        bg: [220, 50, 50],     // Red
        text: `CRASHED`,
        emoji: '💥'
    }
};

const config = PHASE_CONFIG[phase] || PHASE_CONFIG.running;

function createFrame(frameNum) {
    const pixels = new Uint8Array(WIDTH * HEIGHT);
    const progress = frameNum / (FRAMES - 1);
    
    // Calculate pulsing intensity
    const pulse = 0.5 + 0.5 * Math.sin(progress * Math.PI * 4);
    
    // Create gradient effect from center
    const centerX = WIDTH / 2;
    const centerY = HEIGHT / 2;
    const maxDist = Math.sqrt(centerX * centerX + centerY * centerY);
    
    for (let y = 0; y < HEIGHT; y++) {
        for (let x = 0; x < WIDTH; x++) {
            const dx = x - centerX;
            const dy = y - centerY;
            const dist = Math.sqrt(dx * dx + dy * dy);
            const normDist = dist / maxDist;
            
            // Create radial gradient with pulse
            const intensity = Math.max(0, 1 - normDist) * pulse;
            
            // Map to 16-color palette (power of 2)
            // 0-7: dark to medium glow
            // 8-15: medium to bright glow
            let paletteIndex;
            if (intensity < 0.1) {
                paletteIndex = 0; // Dark background
            } else if (intensity < 0.2) {
                paletteIndex = 1;
            } else if (intensity < 0.3) {
                paletteIndex = 2;
            } else if (intensity < 0.4) {
                paletteIndex = 4;
            } else if (intensity < 0.5) {
                paletteIndex = 6;
            } else if (intensity < 0.6) {
                paletteIndex = 8;
            } else if (intensity < 0.7) {
                paletteIndex = 10;
            } else if (intensity < 0.8) {
                paletteIndex = 12;
            } else if (intensity < 0.9) {
                paletteIndex = 14;
            } else {
                paletteIndex = 15; // Brightest
            }
            
            pixels[y * WIDTH + x] = paletteIndex;
        }
    }
    
    return pixels;
}

function generateGIF() {
    try {
        // Create 16-color palette (power of 2)
        // Gradient from dark background to phase color to bright
        const palette = [];
        const bgDark = [30, 31, 35];
        const phaseColor = config.bg;
        const bright = [255, 255, 255];
        
        // Generate smooth gradient (16 colors)
        for (let i = 0; i < 16; i++) {
            const t = i / 15; // 0 to 1
            let r, g, b;
            
            if (t < 0.5) {
                // Dark to phase color
                const t2 = t * 2; // 0 to 1
                r = Math.round(bgDark[0] + (phaseColor[0] - bgDark[0]) * t2);
                g = Math.round(bgDark[1] + (phaseColor[1] - bgDark[1]) * t2);
                b = Math.round(bgDark[2] + (phaseColor[2] - bgDark[2]) * t2);
            } else {
                // Phase color to bright
                const t2 = (t - 0.5) * 2; // 0 to 1
                r = Math.round(phaseColor[0] + (bright[0] - phaseColor[0]) * t2);
                g = Math.round(phaseColor[1] + (bright[1] - phaseColor[1]) * t2);
                b = Math.round(phaseColor[2] + (bright[2] - phaseColor[2]) * t2);
            }
            
            palette.push(r, g, b);
        }
        
        // Create GIF buffer
        const bufferSize = WIDTH * HEIGHT * FRAMES * 2;
        const gifBuffer = new Uint8Array(bufferSize);
        const gif = new GifEncoder(gifBuffer, WIDTH, HEIGHT, {
            palette: palette,
            loop: 0
        });
        
        // Add frames
        for (let i = 0; i < FRAMES; i++) {
            const pixels = createFrame(i);
            gif.addFrame(0, 0, WIDTH, HEIGHT, pixels, {
                delay: Math.round(100 / FPS)  // Delay in 1/100 seconds
            });
        }
        
        // Get actual GIF data
        const gifData = gifBuffer.slice(0, gif.end());
        
        // Write to file
        fs.writeFileSync(outputPath, Buffer.from(gifData));
        console.log(`✅ Generated: ${outputPath}`);
        
    } catch (error) {
        console.error('❌ Error:', error.message);
        process.exit(1);
    }
}

generateGIF();
