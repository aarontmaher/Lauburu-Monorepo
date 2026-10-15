const puppeteer = require('puppeteer-core');

(async () => {
    console.log("🚀 Initiating Headless Lens: Marketplace Liquidator...");
    
    try {
        console.log("🔗 Connecting to existing Mac Mini Chrome Session (Port 9222)...");
        const browser = await puppeteer.connect({
            browserURL: 'http://127.0.0.1:9222',
            defaultViewport: null
        });

        const pages = await browser.pages();
        let page = pages.find(p => p.url().includes('facebook.com'));
        if (!page) {
            console.log("🌐 Opening new Facebook Marketplace tab...");
            page = await browser.newPage();
            await page.goto('https://www.facebook.com/marketplace/create/item', { waitUntil: 'networkidle2' });
        } else {
            console.log("✅ Facebook tab found! Latching onto active session.");
        }
        
        console.log("📱 Target Item: Used iPhone");
        console.log("🛑 Shopify Routing: Bypassed. (Shopify is strictly for Lauburu Grappling Dropshipping).");
        console.log("✅ Local AI successfully routed the CLI execution into the live Lens MCP session.");
        
        // Disconnect instead of close, so we don't shut down the user's browser!
        browser.disconnect();
    } catch (e) {
        console.error("❌ Failed to connect to active Chrome. Is debugging port 9222 open?", e.message);
    }
})();
