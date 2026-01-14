"""Test script to verify the project structure is set up correctly."""

import sys
from pathlib import Path


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")

    try:
        from src.utils.subprocess_tools import run_command, CommandResult

        print("✓ src.utils.subprocess_tools imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import src.utils.subprocess_tools: {e}")
        return False

    try:
        from src.llm.agents.presentation_planner import PresentationPlanner

        print("✓ src.llm.agents.presentation_planner imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import src.llm.agents.presentation_planner: {e}")
        return False

    try:
        from src.pptx.render.node_render import render_html_to_pptx

        print("✓ src.pptx.render.node_render imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import src.pptx.render.node_render: {e}")
        return False

    return True


def test_catalog():
    """Test that the catalog file exists and can be read."""
    print("\nTesting catalog...")

    catalog_path = Path("data/visualisation_store/catalog.json")
    if not catalog_path.exists():
        print(f"✗ Catalog file not found at {catalog_path}")
        return False

    print(f"✓ Catalog file exists at {catalog_path}")

    try:
        import json

        with open(catalog_path) as f:
            catalog = json.load(f)
        print(f"✓ Catalog loaded successfully ({catalog['artifact_count']} artifacts)")
    except Exception as e:
        print(f"✗ Failed to load catalog: {e}")
        return False

    return True


def test_html2pptx():
    """Test that html2pptx files exist."""
    print("\nTesting html2pptx...")

    html2pptx_path = Path("src/pptx/render/js/html2pptx/html2pptx.cjs")
    if not html2pptx_path.exists():
        print(f"✗ html2pptx.cjs not found at {html2pptx_path}")
        return False

    print(f"✓ html2pptx.cjs exists")

    node_modules = Path("src/pptx/render/js/node_modules")
    if not node_modules.exists():
        print(f"✗ node_modules not found at {node_modules}")
        return False

    print(f"✓ node_modules exists")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("PowerPoint Generator - Structure Test")
    print("=" * 60)

    tests = [test_imports, test_catalog, test_html2pptx]

    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append(False)

    print("\n" + "=" * 60)
    if all(results):
        print("✓ All tests passed!")
        print("\nNext steps:")
        print("1. Set your OPENAI_API_KEY environment variable")
        print("2. Run: python main.py 'Show me GIS compliance analysis'")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
