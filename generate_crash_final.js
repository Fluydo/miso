/**
 * Simplified crash GIF generator - definitely works
 * Uses gif-encoder-2 which is more reliable
 */

const fs = require('fs');
const GIFEncoder = require('gif-encoder-2');

const args = process.argv.slice(2);
if (args.length < 3) {
    console.error("Usage: node generate_crash_final.js <phase> <multiplier> <output_path>");
    process.exit(1);
}

const [phase, multiplierStr, outputPath] = args;
const multiplier = parseFloat(multiplierStr);

const WIDTH = 700;
const HEIGHT = 400;
const FPS = 15;
const DURATION = 1;
const FRAMES = FPS * DURATION;

// Phase colors
const COLORS = {
    betting: { r: 254, g: 231, b: 92 },    // Yellow
    running: { r: 34, g: 197, b: 94 },     // Green
    supersonic: { r: 255, g: 140, b: 0 },  // Orange
    crashed: { r: 220, g: 50, b: 50 }      // Red
};

const color = COLORS[phase] || COLORS.running;

async function generateGIF() {
    try {
        const encoder = new GIFEncoder(WIDTH, HEIGHT, 'octree', false);
        encoder.setDelay(1000 / FPS);
        encoder.setRepeat(0);  // Loop forever
        encoder.setQuality(10);
        
        encoder.createReadStream().pipe(fs.createWriteStream(outputPath));
        encoder.start();
        
        // Generate frames
        for (let f = 0; f < FRAMES; f++) {
            const progress = f / (FRAMES - 1);
            const pulse = 0.5 + 0.5 * Math.sin(progress * Math.PI * 4);
            
            // Create RGBA frame
            const frame = Buffer.alloc(WIDTH * HEIGHT * 4);
            
            const centerX = WIDTH / 2;
            const centerY = HEIGHT / 2;
            const maxDist = Math.sqrt(centerX * centerX + centerY * centerY);
            
            for (let y = 0; y < HEIGHT; y++) {
                for (let x = 0; x < WIDTH; x++) {
                    const dx = x - centerX;
                    const dy = y - centerY;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    const normDist = dist / maxDist;
                    
                    // Radial gradient with pulse
                    const intensity = Math.max(0, (1 - normDist) * pulse);
                    
                    const idx = (y * WIDTH + x) * 4;
                    
                    // Dark background + colored glow
                    frame[idx + 0] = Math.round(30 + color.r * intensity);  // R
                    frame[idx + 1] = Math.round(31 + color.g * intensity);  // G
                    frame[idx + 2] = Math.round(35 + color.b * intensity);  // B
                    frame[idx + 3] = 255;  // Alpha
                }
            }
            
            encoder.addFrame(frame);
        }
        
        encoder.finish();
        console.log(`✅ Generated: ${outputPath}`);
        
    } catch (error) {
        console.error('❌ Error:', error.message);
        console.error(error.stack);
        process.exit(1);
    }
}

generateGIF();
