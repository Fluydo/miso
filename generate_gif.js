/**
 * generate_gif.js
 * 
 * Usage: node generate_gif.js <phase> <multiplier> <output_path>
 * Example: node generate_gif.js running 2.5 crash.gif
 */

const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");
const puppeteer = require("puppeteer");

const args = process.argv.slice(2);
if (args.length < 3) {
    console.error("Usage: node generate_gif.js <phase> <multiplier> <output_path>");
    console.error("Example: node generate_gif.js running 2.5 crash.gif");
    process.exit(1);
}

const [phase, multiplierStr, outputPath] = args;
const multiplier = parseFloat(multiplierStr);

const FPS = 15;
const DURATION_MS = 1000; // 1 second per GIF
const VIEWPORT = { width: 700, height: 400 };
const HTML_PATH = "file://" + path.resolve(__dirname, "render_crash.html");

async function generateGIF() {
    const tempDir = path.join(__dirname, ".temp_frames");
    
    // Clean temp dir
    if (fs.existsSync(tempDir)) {
        fs.rmSync(tempDir, { recursive: true });
    }
    fs.mkdirSync(tempDir, { recursive: true });
    
    console.log(`Generating ${phase} @ ${multiplier}x...`);
    
    const browser = await puppeteer.launch({
        headless: "new",
        args: ["--no-sandbox", "--disable-setuid-sandbox"]
    });
    
    const page = await browser.newPage();
    await page.setViewport(VIEWPORT);
    
    // Generate frames with animated progression
    const totalFrames = Math.round((DURATION_MS / 1000) * FPS);
    const startMult = Math.max(1.0, multiplier * 0.7); // Start from 70% of target
    
    for (let f = 0; f < totalFrames; f++) {
        const progress = f / (totalFrames - 1);
        const currentMult = startMult + (multiplier - startMult) * progress;
        
        const url = `${HTML_PATH}?phase=${phase}&multiplier=${currentMult}`;
        await page.goto(url, { waitUntil: "networkidle0" });
        
        // Wait for render complete
        await page.waitForFunction(() => window.renderComplete === true, { timeout: 5000 });
        
        const framePath = path.join(tempDir, `frame-${String(f).padStart(4, "0")}.png`);
        await page.screenshot({
            path: framePath,
            omitBackground: true
        });
    }
    
    await browser.close();
    
    // Convert to GIF with ffmpeg
    console.log("Converting to GIF...");
    const palettePath = path.join(tempDir, "palette.png");
    
    try {
        execSync(
            `ffmpeg -y -framerate ${FPS} -i "${tempDir}/frame-%04d.png" ` +
            `-vf "fps=${FPS},scale=${VIEWPORT.width}:-1:flags=lanczos,palettegen=reserve_transparent=1" ` +
            `"${palettePath}"`,
            { stdio: "inherit" }
        );
        
        execSync(
            `ffmpeg -y -framerate ${FPS} -i "${tempDir}/frame-%04d.png" -i "${palettePath}" ` +
            `-lavfi "fps=${FPS},scale=${VIEWPORT.width}:-1:flags=lanczos [x]; [x][1:v] paletteuse=alpha_threshold=128" ` +
            `-gifflags +transdiff "${outputPath}"`,
            { stdio: "inherit" }
        );
        
        console.log(`✅ Generated: ${outputPath}`);
    } catch (error) {
        console.error("❌ ffmpeg failed:", error.message);
        process.exit(1);
    }
    
    // Cleanup
    fs.rmSync(tempDir, { recursive: true });
}

generateGIF().catch(err => {
    console.error("❌ Error:", err);
    process.exit(1);
});
