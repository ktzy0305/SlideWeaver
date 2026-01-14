/**
 * Generate PowerPoint from HTML table using pptxgenjs
 *
 * NOTE: This runs in the browser, not Node.js
 * PptxGenJS is loaded via <script> tag in index.html
 */

function generatePowerPoint() {
    console.log("Generating PowerPoint presentation...");

    // In pptxgenjs v4.x, use PptxGenJS (capital P)
    // This global is loaded from the <script> tag in index.html
    let pptx = new PptxGenJS();

    // Use tableToSlides to automatically convert the HTML table
    pptx.tableToSlides("riskTable");

    // Write the file
    pptx.writeFile({ fileName: "html2pptx-demo.pptx" });

    console.log("PowerPoint generation complete!");
    alert("PowerPoint file 'html2pptx-demo.pptx' has been generated!");
}

// Log when script loads
console.log("generate.js loaded");
console.log("PptxGenJS available:", typeof PptxGenJS !== 'undefined');