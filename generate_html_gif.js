/**
 * HTML to GIF generator using Puppeteer + gif-encoder + get-pixels
 * NO FFMPEG REQUIRED!
 * Based on: https://dev.to/aimerib/using-puppeteer-to-make-animated-gifs-of-page-scrolls-1lko
 */

const puppeteer = require('puppeteer');
const GIFEncoder = require('gif-encoder');
const fs = require('fs');
const getPixels = require('get-pixels');
const path = require('path');

const args = process.argv.slice(2);
if (args.length < 3) {
    console.error("Usage: node generate_html_gif.js <phase> <multiplier> <output_path>");
    process.exit(1);
}

const [phase, multiplierStr, outputPath] = args;
const multiplier = parseFloat(multiplierStr);

const WIDTH = 700;
const HEIGHT = 400;
const FPS = 15;
const DURATION = 1;  // 1 second
const FRAMES = FPS * DURATION;

// Create temp directory for screenshots
const workDir = './temp_gif_frames/';
if (!fs.existsSync(workDir)) {
    fs.mkdirSync(workDir, { recursive: true });
}

// Helper: Add frames to GIF
function addToGif(images, encoder, counter = 0) {
    return new Promise((resolve, reject) => {
        getPixels(images[counter], function (err, pixels) {
            if (err) {
                reject(err);
                return;
            }
            
            encoder.addFrame(pixels.data);
            encoder.read();
            
            if (counter === images.length - 1) {
                encoder.finish();
                resolve();
            } else {
                addToGif(images, encoder, counter + 1).then(resolve).catch(reject);
            }
        });
    });
}

// Helper: Clean up temp files
function cleanUp(listOfPNGs) {
    listOfPNGs.forEach(filepath => {
        try {
            fs.unlinkSync(filepath);
        } catch (err) {
            console.error(`Failed to delete ${filepath}:`, err.message);
        }
    });
    
    try {
        fs.rmdirSync(workDir);
    } catch (err) {
        // Directory might not be empty or already deleted
    }
}

(async () => {
    try {
        // Create HTML file for rendering
        const htmlPath = path.join(__dirname, 'render_crash.html');
        
        // Setup GIF encoder
        const encoder = new GIFEncoder(WIDTH, HEIGHT);
        const file = fs.createWriteStream(outputPath);
        
        encoder.setFrameRate(FPS);
        encoder.pipe(file);
        encoder.setQuality(10);  // 10 is highest quality
        encoder.setDelay(1000 / FPS);
        encoder.writeHeader();
        encoder.setRepeat(0);  // Loop forever
        
        // Launch Puppeteer
        const browser = await puppeteer.launch({
            headless: 'new',
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
        const page = await browser.newPage();
        await page.setViewport({ width: WIDTH, height: HEIGHT });
        
        // Take screenshots for each frame
        const startMult = Math.max(1.0, multiplier * 0.7);  // Start from 70% of target
        
        for (let i = 0; i < FRAMES; i++) {
            const progress = i / (FRAMES - 1);
            const currentMult = startMult + (multiplier - startMult) * progress;
            
            const url = `file://${htmlPath}?phase=${phase}&multiplier=${currentMult.toFixed(2)}`;
            await page.goto(url, { waitUntil: 'networkidle0' });
            
            // Wait for render
            await page.waitForFunction(() => window.renderComplete === true, { timeout: 3000 });
            
            const framePath = path.join(workDir, `frame-${String(i).padStart(4, '0')}.png`);
            await page.screenshot({
                path: framePath,
                omitBackground: false
            });
        }
        
        await browser.close();
        
        // Get list of PNGs
        let listOfPNGs = fs.readdirSync(workDir)
            .filter(f => f.endsWith('.png'))
            .sort()
            .map(f => path.join(workDir, f));
        
        // Add frames to GIF
        await addToGif(listOfPNGs, encoder);
        
        // Clean up
        cleanUp(listOfPNGs);
        
        console.log(`✅ Generated: ${outputPath}`);
        
    } catch (error) {
        console.error('❌ Error:', error.message);
        process.exit(1);
    }
})();
