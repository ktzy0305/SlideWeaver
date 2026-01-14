import { createRequire } from 'module';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const require = createRequire(import.meta.url);
const pptxgen = require('pptxgenjs');
const html2pptx = require('./js/html2pptx/html2pptx.cjs');

async function main() {
  // Configuration
  const htmlFiles = [
    path.join(__dirname, 'slides', 'slide1.html'),
    path.join(__dirname, 'slides', 'slide2.html'),
    path.join(__dirname, 'slides', 'slide3.html')
  ];
  const outputFile = path.join(__dirname, 'output.pptx');
  const layout = 'LAYOUT_16x9';

  console.log(`Creating PowerPoint presentation with ${htmlFiles.length} slides...`);
  console.log(`Layout: ${layout}`);

  // Create presentation
  const pptx = new pptxgen();
  pptx.layout = layout;

  // Convert each HTML file to a slide
  for (let i = 0; i < htmlFiles.length; i++) {
    const htmlFile = htmlFiles[i];
    console.log(`[${i + 1}/${htmlFiles.length}] Converting: ${path.basename(htmlFile)}`);

    try {
      await html2pptx(htmlFile, pptx);
    } catch (err) {
      console.error(`Failed to convert ${htmlFile}:`, err.message);
      throw err;
    }
  }

  // Write output file
  console.log(`Writing output to: ${outputFile}`);
  await pptx.writeFile({ fileName: outputFile });

  console.log('✓ PowerPoint generation complete!');
}

main().catch((err) => {
  console.error('Error:', err.message);
  if (err.stack) {
    console.error(err.stack);
  }
  process.exit(1);
});