# PowerPoint Generator with Strands Agents

AI-powered PowerPoint presentation generator that uses Strands agents to intelligently select and organize visualizations from a catalog.

## Overview

This tool takes a natural language prompt describing what kind of presentation you want, and automatically:
1. Analyzes your visualization catalog
2. Selects relevant visualizations using multiple strategies (tags, semantic similarity, user prompt matching)
3. Groups visualizations thematically
4. Generates HTML slides
5. Converts them to PowerPoint format

## Setup

### Prerequisites

- Python 3.11+
- Node.js (for html2pptx rendering)
- OpenAI API key

### Installation

1. Install Python dependencies:
```bash
uv pip install openai
```

2. Verify Node.js dependencies are installed:
```bash
cd src/render/js
npm install  # if not already done
```

3. Set your OpenAI API key:
```bash
export OPENAI_API_KEY='your-api-key-here'
```

### Verify Installation

Run the structure test:
```bash
python test_structure.py
```

## Usage

Generate a presentation by providing a natural language prompt:

```bash
python main.py "Show me GIS compliance analysis and polygon quality issues"
```

The tool will:
- Analyze the 11 visualizations in `data/visualisation_store/catalog.json`
- Select and group relevant visualizations
- Generate HTML slides
- Convert to PowerPoint
- Save the output to `output/presentation.pptx`

### Custom Output Path

Specify a custom output path:

```bash
python main.py "Create a compliance overview" --output my-presentation.pptx
```

## Architecture

```
User Prompt
    ↓
main.py (Orchestrator)
    ↓
Strands Agent (PresentationPlanner)
    ├─ Reads catalog.json
    ├─ Selects relevant visualizations
    ├─ Groups by theme
    ├─ Plans slide structure
    └─ Generates HTML files
    ↓
render_html_to_pptx()
    ├─ html2pptx.cjs (HTML → PPTX)
    └─ pptxgenjs library
    ↓
output.pptx
```

## Project Structure

```
powerpoint-generator/
├── src/
│   ├── llm/                        # LLM agents module
│   │   ├── agents/
│   │   │   └── presentation_planner.py    # AI agent for slide planning
│   │   └── template_manager.py     # Template rendering
│   ├── pptx/                       # PowerPoint rendering module
│   │   └── render/
│   │       ├── node_render.py      # Python wrapper for Node.js
│   │       └── js/
│   │           ├── html2pptx/      # HTML to PPTX converter
│   │           └── package.json    # Node.js dependencies
│   ├── utils/                      # Utility modules
│   │   └── subprocess_tools.py     # Subprocess utilities
│   └── templates/                  # Slide templates
│       ├── html/                   # HTML templates
│       │   ├── simple_title.html   # Title slide template
│       │   └── simple_ending.html  # Ending slide template
│       └── css/                    # CSS styles
├── data/
│   └── visualisation_store/
│       ├── catalog.json            # Visualization metadata
│       └── plots/                  # PNG visualization files
├── main.py                         # Main entry point
└── pyproject.toml                  # Python project configuration
```

## Available Visualizations

The catalog contains 11 visualizations across two datasets:
- **Producers dataset** (9 visualizations): Compliance status, GIS compliance, risk assessments
- **Polygons dataset** (2 visualizations): Polygon correction status, issue severity

## Agent Selection Strategy

The Strands agent uses a multi-strategy approach to select visualizations:

1. **Tag matching**: Groups visualizations by shared tags (e.g., "bar plot", "gis compliance")
2. **Semantic similarity**: LLM determines thematic relationships between visualizations
3. **User prompt matching**: Selects visualizations that directly address the user's request

## Example Prompts

- `"Show me an overview of compliance status"`
- `"Create a presentation about GIS compliance and deforestation"`
- `"I need slides showing polygon quality issues"`
- `"Give me a comprehensive compliance analysis"`

## Customization

### HTML Format

The agent generates HTML slides compatible with the existing html2pptx system. Key requirements:
- Slide dimensions: 960x540px (16:9 aspect ratio)
- Supported elements: `<h1>`, `<h2>`, `<p>`, `<img>`, `<ul>`, `<ol>`, `<div>`
- Titles must not exceed 3/4 of slide width
- Text boxes must have 0.5" margin from bottom

### Agent Prompt

Customize the agent's behavior by editing the system prompt in `src/agents/presentation_planner.py`.

## Troubleshooting

### "OPENAI_API_KEY not set"
Set your API key: `export OPENAI_API_KEY='your-key'`

### "Missing node_modules"
Install Node dependencies: `cd src/render/js && npm install`

### "No slides were generated"
Check that:
- The catalog.json file exists and is valid
- Your prompt is clear and specific
- The API key is valid

## Development

Run tests:
```bash
python test_structure.py
```

## License

MIT
