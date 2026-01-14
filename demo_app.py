"""Minimal demo app to generate a PowerPoint slide with a native table."""

import json
from pathlib import Path

from src.pptx.render.node_render import render_html_to_pptx


def create_table_slide(html_table: str, title: str, description: str = "") -> str:
    """Create HTML slide with native table.

    Args:
        html_table: HTML table string from catalog
        title: Slide title
        description: Optional slide description

    Returns:
        HTML string for the slide
    """
    # Add description if provided
    description_html = (
        f'<p class="description">{description}</p>' if description else ""
    )

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{
            width: 960px;
            height: 540px;
            margin: 0;
            padding: 30px;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            overflow: hidden;
        }}
        h1 {{
            font-size: 28px;
            margin: 0 0 10px 0;
            color: #2D3748;
        }}
        .description {{
            font-size: 14px;
            margin: 0 0 15px 0;
            color: #718096;
        }}
        table.dataframe {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        table.dataframe th {{
            background-color: #4A5568;
            color: white;
            padding: 8px 10px;
            text-align: right;
            font-weight: 600;
            border: 1px solid #2D3748;
        }}
        table.dataframe td {{
            padding: 6px 10px;
            border: 1px solid #CBD5E0;
            color: #2D3748;
            text-align: left;
        }}
        table.dataframe tbody tr:nth-child(even) {{
            background-color: #F7FAFC;
        }}
        table.dataframe tbody tr:nth-child(odd) {{
            background-color: white;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    {description_html}
    {html_table}
</body>
</html>"""

    return html


def main():
    """Main demo function."""
    print("=== PowerPoint Table Demo ===\n")

    # Load catalog
    catalog_path = Path("data/visualisation_store/catalog.json")
    print(f"Loading catalog from {catalog_path}...")

    with open(catalog_path) as f:
        catalog = json.load(f)

    # Get third artifact (index 2)
    artifacts = catalog["artifacts"]
    if len(artifacts) < 3:
        print("Error: Not enough artifacts in catalog")
        return

    third_artifact = artifacts[1]  # Third artifact (0-indexed)

    print(f"Selected artifact: {third_artifact['artifact_id']}")
    print(f"Title: {third_artifact['title']}")
    print(f"Description: {third_artifact['description']}\n")

    # Get HTML table
    html_table = third_artifact.get("html_table")
    if not html_table:
        print("Error: Third artifact has no html_table")
        return

    print("HTML table preview:")
    print(html_table[:200] + "...\n")

    # Create HTML slide with table
    print("Creating HTML slide with native table...")
    html_content = create_table_slide(
        html_table, third_artifact["title"], third_artifact["description"]
    )

    # Save HTML to temporary file
    output_dir = Path("output/demo")
    output_dir.mkdir(parents=True, exist_ok=True)

    html_path = output_dir / "table_slide.html"
    html_path.write_text(html_content, encoding="utf-8")
    print(f"HTML slide saved to: {html_path}")

    # Generate PowerPoint
    print("\nConverting to PowerPoint...")
    pptx_path = Path("output/demo/table_demo.pptx")
    js_workspace = Path("src/pptx/render/js")
    html2pptx_js = js_workspace / "html2pptx" / "html2pptx.cjs"

    returncode, stdout, stderr = render_html_to_pptx(
        html_files=[html_path],
        output_pptx=pptx_path,
        js_workspace=js_workspace,
        html2pptx_js=html2pptx_js,
        layout="LAYOUT_16x9",
    )

    if returncode != 0:
        print(f"\n❌ Error generating PowerPoint:")
        print(stderr)
        return

    if stdout:
        print(stdout)

    print(f"\n✅ Success! PowerPoint saved to: {pptx_path.resolve()}")
    print(f"\nThe table has been rendered as a native PowerPoint table.")
    print(f"You can open {pptx_path.name} to verify the table is editable.")


if __name__ == "__main__":
    main()
