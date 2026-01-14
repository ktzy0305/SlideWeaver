const { chromium } = require('playwright');
const path = require('path');

const { validateDimensions, validateTextBoxPosition, wrapAndValidateTitles } = require('./validators.cjs');
const { addBackground, addElements } = require('./pptx_generator.cjs');
const { getBodyDimensions, extractSlideData } = require('./dom_scanner.cjs');

/**
 * Main function to convert HTML file to PowerPoint slide
 * 
 * @param {string} htmlFile - Path to the HTML file
 * @param {PptxGenJS} presentation - PptxGenJS presentation instance
 * @param {object} options - Options object (tmpDir, slide)
 * @returns {Promise<{slide: object, placeholders: Array}>}
 */
async function html2pptx(htmlFile, presentation, options = {}) {
  const {
    tmpDir = process.env.TMPDIR || '/tmp',
    slide = null
  } = options;

  try {
    // Use Chrome on macOS, default Chromium on Unix
    const launchOptions = { env: { TMPDIR: tmpDir } };
    if (process.platform === 'darwin') {
      launchOptions.channel = 'chrome';
    }

    const browser = await chromium.launch(launchOptions);

    let bodyDimensions;
    let slideData;

    const filePath = path.isAbsolute(htmlFile) ? htmlFile : path.join(process.cwd(), htmlFile);
    const validationErrors = [];

    try {
      const page = await browser.newPage();
      page.on('console', (msg) => {
        // Log the message text to your test runner's console
        console.log(`Browser console: ${msg.text()}`);
      });

      await page.goto(`file://${filePath}`);

      // Enforce title constraints early so layout measurements reflect wrapped titles.
      // Requirement: title should not exceed 3/4 of slide width; wrap at whole-word boundaries.
      const titleErrors = await wrapAndValidateTitles(page, 0.75);
      if (titleErrors.length > 0) {
        validationErrors.push(...titleErrors);
      }

      // Extract dimensions from the rendered page
      bodyDimensions = await getBodyDimensions(page);

      // Set viewport to match content dimensions for accurate rendering
      await page.setViewportSize({
        width: Math.round(bodyDimensions.width),
        height: Math.round(bodyDimensions.height)
      });

      // Extract all element data from the page
      slideData = await extractSlideData(page);
    } finally {
      await browser.close();
    }

    // Collect all validation errors from various stages
    if (bodyDimensions.errors && bodyDimensions.errors.length > 0) {
      validationErrors.push(...bodyDimensions.errors);
    }

    const dimensionErrors = validateDimensions(bodyDimensions, presentation);
    if (dimensionErrors.length > 0) {
      validationErrors.push(...dimensionErrors);
    }

    const textBoxPositionErrors = validateTextBoxPosition(slideData, bodyDimensions);
    if (textBoxPositionErrors.length > 0) {
      validationErrors.push(...textBoxPositionErrors);
    }

    if (slideData.errors && slideData.errors.length > 0) {
      validationErrors.push(...slideData.errors);
    }

    // Throw all errors at once if any exist
    if (validationErrors.length > 0) {
      const errorMessage = validationErrors.length === 1
        ? validationErrors[0]
        : `Multiple validation errors found:\n${validationErrors.map((e, i) => `  ${i + 1}. ${e}`).join('\n')}`;
      throw new Error(errorMessage);
    }

    // Add content to the slide
    const targetSlide = slide || presentation.addSlide();

    await addBackground(slideData, targetSlide, tmpDir);
    await addElements(slideData, targetSlide, presentation);

    return { slide: targetSlide, placeholders: slideData.placeholders };
  } catch (error) {
    // Ensure error context includes the file path
    if (!error.message.startsWith(htmlFile)) {
      throw new Error(`${htmlFile}: ${error.message}`);
    }
    throw error;
  }
}

module.exports = html2pptx;
