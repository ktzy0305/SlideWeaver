  # HTML2PPTX + PPTXGenJS Architecture Overview

  1. html2pptx.cjs (Main Orchestrator)

  - Launches Chromium/Chrome browser via Playwright
  - Loads the HTML file in the browser
  - Validates titles, dimensions, and text positions
  - Coordinates the workflow: scan DOM → validate → generate PPTX
  - Returns the slide and placeholders

  2. dom_scanner.cjs (DOM Scanning)

  This is the most complex file (~670 lines). It has two main functions:

  - getBodyDimensions(page): Measures body size and detects overflow
  - extractSlideData(page): Runs getSlideDataFromDom() in the browser context

  The getSlideDataFromDom() function is self-contained and serialized to run in the browser. It:
  - Scans all elements in the DOM
  - Converts them to a JSON structure with type, position, style, and content
  - Currently handles:
    - Text: p, h1-h6 (with inline formatting via parseInlineFormatting())
    - Lists: ul, ol with bullet handling
    - Images: img with src and positioning
    - Shapes: div with background color, borders, shadows
    - Lines: Individual border sides when borders are non-uniform
    - Placeholders: Elements with class placeholder

  3. pptx_generator.cjs (PPTX Generation)

  - addBackground(): Sets slide background (image or color)
  - addElements(): Iterates through extracted elements and calls PptxGenJS API:
    - targetSlide.addImage() for images (with aspect-fit logic)
    - targetSlide.addShape() for lines and rectangles
    - targetSlide.addText() for text, lists, and shapes with text

  4. validators.cjs (Layout Validation)

  - wrapAndValidateTitles(): Wraps H1 titles at word boundaries (max 75% slide width)
  - validateDimensions(): Ensures HTML matches presentation dimensions
  - validateTextBoxPosition(): Ensures text doesn't overflow bottom margin (0.5")

  5. utils.cjs (Utilities)

  - Constants: PT_PER_PX = 0.75, PX_PER_IN = 96, EMU_PER_IN = 914400
  - Path normalization and file validation

  To Add Native Table Support

  Based on this architecture, you would need to:

  1. In dom_scanner.cjs (around line 313):
    - Add 'TABLE' to the list of elements to scan
    - Create a table extraction function that scans <table>, <tr>, <td>, <th> elements
    - Extract cell content, styles, borders, colors, etc.
    - Return a structured table object with rows, columns, and cell data
  2. In pptx_generator.cjs (around line 123):
    - Add a new condition: else if (element.type === 'table')
    - Call PptxGenJS's table API: targetSlide.addTable(rows, options)
    - Map the extracted table data to PptxGenJS format
  3. In validators.cjs (optional):
    - Add table-specific validation if needed (e.g., ensure table fits within slide bounds)

  Does this match your understanding? Would you like me to help you implement table support?