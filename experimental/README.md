# PptxGenJS Table Experiment

This is an experimental project to test the `tableToSlides()` feature of pptxgenjs.

## Setup

Already done! The dependencies are installed.

```bash
npm install  # Already completed
```

## How to Use

**Important:** You need to run a local web server because browsers block loading scripts from `node_modules` when using `file://` protocol.

### Option 1: Using npm start (Recommended)

```bash
cd experimental_dev
npm start
```

Then open your browser to: http://localhost:8000

### Option 2: Using Python's built-in server

```bash
cd experimental_dev
python3 -m http.server 8000
```

Then open your browser to: http://localhost:8000

### Option 3: Use the CDN version (no server needed)

See `index-cdn.html` which loads pptxgenjs from a CDN instead of node_modules.

---

Once the page loads:

1. **Click the "Generate PowerPoint" button**
   - This will use pptxgenjs's `tableToSlides("riskTable")` method
   - A file named `html2pptx-demo.pptx` will be downloaded

2. **Open the PowerPoint file** to see the result

## Files

- `index.html` - HTML page with a sample data table
- `generate.js` - JavaScript code that generates the PowerPoint
- `package.json` - Node.js dependencies
- `node_modules/` - Installed packages (pptxgenjs)

## The Key Code

```javascript
let pptx = new pptxgen();
pptx.tableToSlides("riskTable");
pptx.writeFile({ fileName: "html2pptx-demo.pptx" });
```

This uses pptxgenjs's built-in `tableToSlides()` method which:
- Reads an HTML table by ID
- Automatically converts it to PowerPoint slides
- Creates native PowerPoint table objects (editable!)

## Next Steps

After testing this, you can:
1. Modify the table structure in `index.html`
2. Experiment with different table styles
3. Try the declarative API to programmatically create tables
4. Test multi-slide generation for large tables

## Notes

- The table is converted to a **native PowerPoint table** (not an image)
- Styling from HTML/CSS may not transfer perfectly
- pptxgenjs handles pagination automatically for large tables
