# Table Demo App

A minimal working demo that generates a PowerPoint slide with a native editable table.

## What it does

The `demo_app.py` script:

1. **Loads the visualization catalog** from `data/visualisation_store/catalog.json`
2. **Extracts the third artifact's HTML table** (Risk Categories data)
3. **Creates an HTML slide template** with:
   - Title from the artifact
   - Description text
   - Native HTML table with styled headers and rows
4. **Generates a PowerPoint file** with the table rendered as a native PowerPoint table (not an image!)

## How to run

```bash
python demo_app.py
```

## Output

The demo creates:
- `output/demo/table_slide.html` - HTML slide with the table
- `output/demo/table_demo.pptx` - PowerPoint file with native table

## Key features

- **Native PowerPoint tables**: The table is editable in PowerPoint, not a static image
- **Styled tables**: Professional styling with:
  - Header row with dark background
  - Alternating row colors for readability
  - Borders and proper spacing
  - Responsive sizing
- **Automatic layout**: 960px × 540px (16:9 aspect ratio)

## How it works

The demo uses:
1. **HTML table from catalog** - Takes the pre-formatted `html_table` field
2. **CSS styling** - Adds professional table styles
3. **html2pptx converter** - Converts HTML to native PowerPoint elements
4. **subprocess_tools** - Executes Node.js rendering pipeline

## Example output

The demo generates a slide with the "Non-Compliance Risk Categories" data table showing:
- Assessment types (land legality, environmental status, etc.)
- Risk levels (Low Risk, High Risk)
- Counts and percentages

The table has **8 data rows** and **4 columns**, all fully editable in PowerPoint.

## Technical notes

- The HTML table uses the `dataframe` class (from pandas output)
- Styling is applied via inline CSS in the `<style>` tag
- The html2pptx converter recognizes `<table>` elements and converts them to native PowerPoint tables
- Table dimensions auto-fit to the slide layout
