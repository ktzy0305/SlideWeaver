#!/usr/bin/env node
/**
 * CLI wrapper for html2pptx converter
 * Usage: node cli.cjs --input <slides_dir> --output <output.pptx>
 */

const fs = require('fs');
const path = require('path');
const pptxgen = require('pptxgenjs');
const html2pptx = require('./html2pptx.cjs');

function parseArgs() {
  const args = process.argv.slice(2);
  const options = {
    input: null,
    output: null,
  };

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--input' && args[i + 1]) {
      options.input = args[++i];
    } else if (args[i] === '--output' && args[i + 1]) {
      options.output = args[++i];
    }
  }

  return options;
}

async function main() {
  const options = parseArgs();

  if (!options.input || !options.output) {
    console.error('Usage: node cli.cjs --input <slides_dir> --output <output.pptx>');
    process.exit(1);
  }

  const inputDir = path.resolve(options.input);
  const outputFile = path.resolve(options.output);

  // Check input directory exists
  if (!fs.existsSync(inputDir)) {
    console.error(`Input directory not found: ${inputDir}`);
    process.exit(1);
  }

  // Get all HTML files in the input directory, sorted
  const htmlFiles = fs.readdirSync(inputDir)
    .filter(f => f.endsWith('.html'))
    .sort()
    .map(f => path.join(inputDir, f));

  if (htmlFiles.length === 0) {
    console.error(`No HTML files found in: ${inputDir}`);
    process.exit(1);
  }

  console.log(`Converting ${htmlFiles.length} slides to PPTX...`);

  // Create presentation
  const pptx = new pptxgen();
  pptx.layout = 'LAYOUT_16x9';

  // Convert each HTML file to a slide
  for (let i = 0; i < htmlFiles.length; i++) {
    const htmlFile = htmlFiles[i];
    console.log(`  [${i + 1}/${htmlFiles.length}] ${path.basename(htmlFile)}`);

    try {
      await html2pptx(htmlFile, pptx);
    } catch (err) {
      console.error(`  Failed to convert ${path.basename(htmlFile)}: ${err.message}`);
      // Continue with other slides
    }
  }

  // Ensure output directory exists
  const outputDir = path.dirname(outputFile);
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  // Write output file
  console.log(`Writing: ${outputFile}`);
  await pptx.writeFile({ fileName: outputFile });

  console.log('Done!');
}

main().catch((err) => {
  console.error('Error:', err.message);
  process.exit(1);
});
