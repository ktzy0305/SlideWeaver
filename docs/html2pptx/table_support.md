Now let me design the implementation plan. Based on the PptxGenJS API research, here's the complete plan:

  Implementation Plan for Table Support in html2pptx

  1. dom_scanner.cjs - Table Extraction Logic

  Location: Add table scanning in the main document.querySelectorAll('*') loop around line 313

  Table Detection & Structure Extraction:

  ```
  if (element.tagName === 'TABLE') {
    const rect = element.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;

    // Extract table structure
    const tableData = extractTableData(element, rect);

    elements.push({
      type: 'table',
      position: {
        x: pxToInch(rect.left),
        y: pxToInch(rect.top),
        w: pxToInch(rect.width),
        h: pxToInch(rect.height)
      },
      rows: tableData.rows,
      style: tableData.style
    });

    processed.add(element);
    // Also mark all child elements as processed
    element.querySelectorAll('tr, td, th').forEach(el => processed.add(el));
    return;
  }

  New Helper Function - extractTableData(table, rect):
  const extractTableData = (table, rect) => {
    const computed = window.getComputedStyle(table);
    const rows = [];

    // Get all rows (thead and tbody)
    const trElements = Array.from(table.querySelectorAll('tr'));

    trElements.forEach((tr, rowIdx) => {
      const cells = [];
      const cellElements = Array.from(tr.children); // td or th

      cellElements.forEach((cell) => {
        const cellComputed = window.getComputedStyle(cell);
        const isHeader = cell.tagName === 'TH';

        // Extract cell content (support inline formatting)
        const hasFormatting = cell.querySelector('b, i, u, strong, em, span, a, br');
        let cellText;

        if (hasFormatting) {
          // Use parseInlineFormatting for rich text
          cellText = parseInlineFormatting(cell, {}, [], (x) => x);
        } else {
          // Plain text
          cellText = cell.textContent.trim();
        }

        // Extract cell styles
        const cellOptions = {
          bold: isHeader || cellComputed.fontWeight === 'bold' || parseInt(cellComputed.fontWeight) >= 600,
          italic: cellComputed.fontStyle === 'italic',
          underline: cellComputed.textDecoration && cellComputed.textDecoration.includes('underline'),
          fontSize: pxToPoints(cellComputed.fontSize),
          fontFace: cellComputed.fontFamily.split(',')[0].replace(/['"]/g, '').trim(),
          color: rgbToHex(cellComputed.color),
          fill: cellComputed.backgroundColor && cellComputed.backgroundColor !== 'rgba(0, 0, 0, 0)'
            ? rgbToHex(cellComputed.backgroundColor)
            : null,
          align: cellComputed.textAlign === 'start' ? 'left' : cellComputed.textAlign,
          valign: cellComputed.verticalAlign || 'top',
          margin: pxToPoints(cellComputed.padding)
        };

        // Handle borders
        const borderTop = parseFloat(cellComputed.borderTopWidth) || 0;
        const borderColor = cellComputed.borderColor || cellComputed.borderTopColor;
        if (borderTop > 0) {
          cellOptions.border = {
            type: 'solid',
            pt: borderTop * PT_PER_PX,
            color: rgbToHex(borderColor)
          };
        }

        // Handle colspan and rowspan
        const colspan = parseInt(cell.getAttribute('colspan')) || 1;
        const rowspan = parseInt(cell.getAttribute('rowspan')) || 1;
        if (colspan > 1) cellOptions.colspan = colspan;
        if (rowspan > 1) cellOptions.rowspan = rowspan;

        cells.push({
          text: cellText,
          options: cellOptions
        });
      });

      rows.push(cells);
    });

    // Extract table-level styles
    const style = {
      border: null, // Extract from computed style if uniform
      colW: null,   // Could calculate from cell widths
      rowH: null    // Could calculate from cell heights
    };

    return { rows, style };
  };
  ```

  Key Considerations:
  - Detect <thead> rows vs <tbody> rows (th vs td)
  - Support both plain text and rich text in cells (using existing parseInlineFormatting)
  - Extract cell-level borders, colors, alignment
  - Handle colspan and rowspan attributes
  - Calculate column widths from actual rendered widths
  - Mark all table child elements as processed to avoid duplicate processing

  ---

⏺ 2. pptx_generator.cjs - Table Generation Logic

  Location: Add in addElements() function around line 123, after the image handling block

  else if (element.type === 'table') {
    // Convert extracted table data to PptxGenJS format
    const pptxRows = [];

    for (const row of element.rows) {
      const pptxRow = [];

      for (const cell of row) {
        // Build cell object for PptxGenJS
        const pptxCell = {
          text: cell.text,
          options: {}
        };

        // Map cell options to PptxGenJS format
        if (cell.options.bold) pptxCell.options.bold = true;
        if (cell.options.italic) pptxCell.options.italic = true;
        if (cell.options.underline) pptxCell.options.underline = true;
        if (cell.options.fontSize) pptxCell.options.fontSize = cell.options.fontSize;
        if (cell.options.fontFace) pptxCell.options.fontFace = cell.options.fontFace;
        if (cell.options.color) pptxCell.options.color = cell.options.color;
        if (cell.options.fill) pptxCell.options.fill = cell.options.fill;
        if (cell.options.align) pptxCell.options.align = cell.options.align;
        if (cell.options.valign) pptxCell.options.valign = cell.options.valign;
        if (cell.options.margin !== undefined) pptxCell.options.margin = cell.options.margin;
        if (cell.options.border) pptxCell.options.border = cell.options.border;
        if (cell.options.colspan) pptxCell.options.colspan = cell.options.colspan;
        if (cell.options.rowspan) pptxCell.options.rowspan = cell.options.rowspan;

        pptxRow.push(pptxCell);
      }

      pptxRows.push(pptxRow);
    }

    // Build table-level options
    const tableOptions = {
      x: element.position.x,
      y: element.position.y,
      w: element.position.w,
      h: element.position.h
    };

    // Add table-level styles if present
    if (element.style.border) tableOptions.border = element.style.border;
    if (element.style.colW) tableOptions.colW = element.style.colW;
    if (element.style.rowH) tableOptions.rowH = element.style.rowH;

    // Add table to slide
    targetSlide.addTable(pptxRows, tableOptions);
  }

  Key Considerations:
  - Transform extracted table structure to PptxGenJS format
  - Map all cell-level options correctly
  - Handle rich text cells (arrays of text runs)
  - Preserve position and dimensions
  - Pass through colspan/rowspan values
  - Handle cases where cells have no options (plain strings)

  ---

⏺ 3. validators.cjs - Table Validation Rules

  New Function: validateTables(slideData, bodyDimensions)

  Location: Add as a new exported function at the end of validators.cjs

  /**
   * Validate table structure and positioning
   * 
   * @param {object} slideData - Extracted slide data containing tables
   * @param {object} bodyDimensions - Body dimensions from scanner
   * @returns {string[]} Array of validation error messages
   */
  function validateTables(slideData, bodyDimensions) {
    const errors = [];
    const slideWidthInches = bodyDimensions.width / PX_PER_IN;
    const slideHeightInches = bodyDimensions.height / PX_PER_IN;

    for (const element of slideData.elements) {
      if (element.type !== 'table') continue;

      // 1. Validate table fits within slide bounds
      const tableRight = element.position.x + element.position.w;
      const tableBottom = element.position.y + element.position.h;

      if (tableRight > slideWidthInches) {
        errors.push(
          `Table extends beyond slide width by ${(tableRight - slideWidthInches).toFixed(2)}". ` +
          `Reduce table width or adjust positioning.`
        );
      }

      if (tableBottom > slideHeightInches - 0.5) { // 0.5" bottom margin
        errors.push(
          `Table extends too close to bottom edge (ends at ${tableBottom.toFixed(2)}", ` +
          `slide height ${slideHeightInches.toFixed(2)}"). Leave 0.5" margin at bottom.`
        );
      }

      // 2. Validate table has rows
      if (!element.rows || element.rows.length === 0) {
        errors.push(`Table is empty - no rows found.`);
        continue;
      }

      // 3. Validate consistent column count
      const firstRowCellCount = element.rows[0].length;
      element.rows.forEach((row, idx) => {
        // Account for colspan: sum up the effective columns
        const effectiveColumns = row.reduce((sum, cell) => {
          return sum + (cell.options?.colspan || 1);
        }, 0);

        if (idx === 0) return; // Skip first row comparison

        // Allow some flexibility for rowspan/colspan combinations
        // Just warn if significantly different
        if (Math.abs(effectiveColumns - firstRowCellCount) > 2) {
          errors.push(
            `Table row ${idx + 1} has inconsistent column count ` +
            `(${effectiveColumns} vs ${firstRowCellCount} in first row). ` +
            `Check colspan/rowspan usage.`
          );
        }
      });

      // 4. Validate cell text isn't too long (PowerPoint limitations)
      element.rows.forEach((row, rowIdx) => {
        row.forEach((cell, cellIdx) => {
          const cellText = typeof cell.text === 'string'
            ? cell.text
            : Array.isArray(cell.text)
              ? cell.text.map(r => r.text).join('')
              : '';

          if (cellText.length > 5000) {
            errors.push(
              `Table cell at row ${rowIdx + 1}, column ${cellIdx + 1} ` +
              `contains ${cellText.length} characters (max recommended: 5000). ` +
              `Consider splitting content.`
            );
          }
        });
      });

      // 5. Validate rowspan/colspan values are reasonable
      element.rows.forEach((row, rowIdx) => {
        row.forEach((cell, cellIdx) => {
          const colspan = cell.options?.colspan;
          const rowspan = cell.options?.rowspan;

          if (colspan && colspan > firstRowCellCount) {
            errors.push(
              `Table cell at row ${rowIdx + 1}, column ${cellIdx + 1} ` +
              `has colspan=${colspan} but table only has ${firstRowCellCount} columns.`
            );
          }

          if (rowspan && rowspan > element.rows.length) {
            errors.push(
              `Table cell at row ${rowIdx + 1}, column ${cellIdx + 1} ` +
              `has rowspan=${rowspan} but table only has ${element.rows.length} rows.`
            );
          }
        });
      });
    }

    return errors;
  }

  module.exports = {
    validateDimensions,
    validateTextBoxPosition,
    wrapAndValidateTitles,
    validateTables  // Add to exports
  };

  Integration in html2pptx.cjs:
  // After line 78 (textBoxPositionErrors)
  const tableErrors = validateTables(slideData, bodyDimensions);
  if (tableErrors.length > 0) {
    validationErrors.push(...tableErrors);
  }

  Validation Rules Summary:
  1. ✅ Table fits within slide bounds (width and height)
  2. ✅ Table respects bottom margin (0.5")
  3. ✅ Table has at least one row
  4. ✅ Rows have consistent column counts (accounting for colspan)
  5. ✅ Cell text doesn't exceed reasonable length limits
  6. ✅ Rowspan/colspan values don't exceed table dimensions

  ---

⏺ 4. Complete Implementation Plan Document

  Table Support Implementation Plan for html2pptx

  Overview

  Add native HTML table support to the html2pptx module by extending DOM scanning, PPTX generation, and validation capabilities.

  Files to Modify

  1. experimental/js/html2pptx/dom_scanner.cjs (~100 lines added)
  2. experimental/js/html2pptx/pptx_generator.cjs (~50 lines added)
  3. experimental/js/html2pptx/validators.cjs (~120 lines added)
  4. experimental/js/html2pptx/html2pptx.cjs (~5 lines added)

  ---
  Phase 1: DOM Scanner Enhancement

  File: experimental/js/html2pptx/dom_scanner.cjs

  Changes:
  - Add table detection in main element loop (line ~313)
  - Create new helper function extractTableData() inside getSlideDataFromDom()
  - Process <table>, <thead>, <tbody>, <tr>, <th>, <td> elements
  - Extract table structure: rows → cells → text/options
  - Mark all table children as processed to avoid duplicates

  Data Structure Output:
  {
    type: 'table',
    position: { x, y, w, h },  // in inches
    rows: [
      [
        {
          text: "Cell content" | [{text, options}],  // string or rich text
          options: {
            bold, italic, underline,
            fontSize, fontFace, color, fill,
            align, valign, margin,
            border: {type, pt, color},
            colspan, rowspan
          }
        },
        ...
      ],
      ...
    ],
    style: {
      border, colW, rowH  // table-level defaults
    }
  }

  Key Features:
  - Support both TH (header) and TD (data) cells
  - Detect and preserve colspan/rowspan attributes
  - Extract cell-level styling (colors, borders, alignment, fonts)
  - Support rich text in cells via parseInlineFormatting()
  - Calculate dimensions from rendered layout

  ---
  Phase 2: PPTX Generator Enhancement

  File: experimental/js/html2pptx/pptx_generator.cjs

  Changes:
  - Add else if (element.type === 'table') block in addElements() (line ~123)
  - Transform extracted table data to PptxGenJS format
  - Map cell options to PptxGenJS API expectations
  - Call targetSlide.addTable(rows, options)

  Transformation Logic:
  // Input: element.rows from scanner
  // Output: PptxGenJS format
  [
    [
      { text: "Header 1", options: { fill: "0088cc", bold: true } },
      { text: "Header 2", options: { fill: "0088cc", bold: true } }
    ],
    [
      { text: "Data 1", options: { align: "left" } },
      { text: "Data 2", options: { align: "right" } }
    ]
  ]

  Mapping:
  - Bold, italic, underline → direct mapping
  - Colors (fill, text color) → hex format
  - Alignment (align, valign) → PptxGenJS values
  - Borders → {type, pt, color} object
  - Colspan/rowspan → direct pass-through
  - Position/size → table-level options

  ---
  Phase 3: Validation Enhancement

  File: experimental/js/html2pptx/validators.cjs

  Changes:
  - Add new function validateTables(slideData, bodyDimensions)
  - Export in module.exports
  - Call from html2pptx.cjs after other validations

  Validation Checks:
  1. Bounds checking: Table doesn't overflow slide width/height
  2. Bottom margin: Maintains 0.5" margin from bottom
  3. Structure: Table has at least one row
  4. Consistency: Rows have similar column counts (accounting for colspan)
  5. Content limits: Cell text doesn't exceed 5000 characters
  6. Span validity: Rowspan/colspan values are within table dimensions

  Error Messages:
  - Clear, actionable error descriptions
  - Include row/column indices for cell-specific issues
  - Suggest remediation (reduce width, check colspan, etc.)

  ---
  Phase 4: Integration

  File: experimental/js/html2pptx/html2pptx.cjs

  Changes (line ~78):
  const tableErrors = validateTables(slideData, bodyDimensions);
  if (tableErrors.length > 0) {
    validationErrors.push(...tableErrors);
  }

  ---
  Testing Strategy

  Test Cases:
  1. ✅ Simple 2x3 table (2 rows, 3 columns)
  2. ✅ Table with header row (TH cells)
  3. ✅ Table with cell styling (colors, borders, fonts)
  4. ✅ Table with colspan (2-3 columns merged)
  5. ✅ Table with rowspan (2-3 rows merged)
  6. ✅ Table with rich text in cells (bold, links, formatting)
  7. ✅ Table that overflows (validation error)
  8. ✅ Multiple tables on one slide
  9. ✅ Empty table (validation error)
  10. ✅ Inconsistent row structure (validation error)

  Test File: experimental/slides/slide2.html (already contains table HTML)

  ---
  Edge Cases & Limitations

  Supported:
  - ✅ Basic tables with rows and columns
  - ✅ Header rows (thead/th) with distinct styling
  - ✅ Cell-level formatting (colors, fonts, alignment)
  - ✅ Borders (solid, uniform thickness per cell)
  - ✅ Colspan and rowspan
  - ✅ Rich text in cells (inline formatting)
  - ✅ Multiple tables per slide

  Not Supported (Future):
  - ❌ Nested tables
  - ❌ Complex border styles (dashed, dotted) - need CSS parsing
  - ❌ Variable border widths per side (top/bottom/left/right different)
  - ❌ Background images in cells
  - ❌ Auto-paging (table overflow to next slide)
  - ❌ Cell padding as TRBL array (only uniform padding)

  Assumptions:
  - Tables use border-collapse: collapse
  - Borders are uniform thickness per cell
  - Font sizes are reasonable (8-24pt typically)
  - Cell content is primarily text (not complex nested HTML)

  ---
  Implementation Order

  1. DOM Scanner (dom_scanner.cjs) - Extract tables
  2. PPTX Generator (pptx_generator.cjs) - Render tables
  3. Validators (validators.cjs) - Validate tables
  4. Integration (html2pptx.cjs) - Wire up validation
  5. Testing - Run orchestrator with slide2.html

  Each phase builds on the previous, allowing incremental testing.

  ---

⏺ Summary: Table Support Implementation Plan

  I've completed planning the table support implementation for html2pptx. Here's the comprehensive plan:

  Architecture Overview

  The implementation follows the existing html2pptx architecture with 4 key modifications:

  1. DOM Scanner (dom_scanner.cjs) - Extract table structure from HTML
    - Scan <table> elements and children
    - Extract rows, cells, text, and styling
    - Support colspan/rowspan attributes
    - ~100 lines added
  2. PPTX Generator (pptx_generator.cjs) - Render tables in PowerPoint
    - Transform extracted data to PptxGenJS format
    - Map cell options (colors, fonts, borders, alignment)
    - Call slide.addTable(rows, options)
    - ~50 lines added
  3. Validators (validators.cjs) - Validate table structure
    - Check bounds (fits within slide)
    - Validate row/column consistency
    - Verify colspan/rowspan values
    - Enforce bottom margin
    - ~120 lines added
  4. Integration (html2pptx.cjs) - Wire up validation
    - Call validateTables() during validation phase
    - ~5 lines added

  PptxGenJS Table Format (from official docs)

  // Rows = array of arrays
  // Cells = {text, options} or plain strings
  const rows = [
    [
      { text: "Header 1", options: { fill: "0088cc", bold: true } },
      { text: "Header 2", options: { fill: "0088cc", bold: true } }
    ],
    [
      "Data 1",  // Plain string
      { text: "Data 2", options: { align: "right" } }
    ]
  ];

  slide.addTable(rows, { x: 1, y: 1, w: 8, h: 4 });

  Key Features Planned

  ✅ Basic table structure (rows/columns)
  ✅ Header rows (TH) with distinct styling
  ✅ Cell-level formatting (colors, fonts, borders, alignment)
  ✅ Colspan and rowspan support
  ✅ Rich text in cells (bold, italic, links)
  ✅ Multiple tables per slide
  ✅ Comprehensive validation (bounds, structure, consistency)

  Test Strategy

  The existing experimental/slides/slide2.html already contains a table - perfect for testing once implemented!

  Ready for Implementation?

  The plan is complete and ready for proofreading. Once approved, we can implement in the order:
  1. DOM Scanner → 2. PPTX Generator → 3. Validators → 4. Integration → 5. Testing

  Would you like to review the plan in more detail, or should we proceed with implementation?

  ---
  Sources:
  - https://gitbrent.github.io/PptxGenJS/docs/api-tables.html
  - https://github.com/gitbrent/PptxGenJS/blob/master/demos/modules/demo_table.mjs