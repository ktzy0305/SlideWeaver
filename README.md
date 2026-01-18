# 🧵 SlideWeaver

AI-powered presentation generator that weaves your ideas into beautiful slide decks. Using intelligent agents, SlideWeaver automatically selects visualizations, plans slide structure, and designs professional presentations.

## Features

- **Natural Language Input** - Describe what you want, SlideWeaver weaves it together
- **Smart Visualization Selection** - Automatically picks relevant charts and images
- **AI-Powered Design** - Each slide is crafted with proper layout and styling
- **Editable Tables** - Generate tables that remain fully editable in PowerPoint
- **Real-time Progress** - Watch your presentation come to life
- **Web & CLI** - Use the beautiful web interface or command line

## Prerequisites

- Python 3.11+
- Node.js 18+
- OpenAI API key

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ktzy0305/SlideWeaver.git
   cd powerpoint-generator
   ```

2. **Install Python dependencies**
   ```bash
   pip install -e .
   ```
   Or with uv:
   ```bash
   uv pip install -e .
   ```

3. **Install Node.js dependencies**
   ```bash
   npm install
   ```

## Configuration

Copy the example config and customize as needed:

```bash
cp configs/config.yaml.example configs/config.yaml
```

Configuration options in `configs/config.yaml`:

```yaml
api:
  host: "0.0.0.0"
  port: 8000

defaults:
  audience: "General business audience"
  tone: "executive"
  model_id: "gpt-5.2"

timeouts:
  converter: 120
  api_request: 300
```

## Running the Application

### Option 1: Web Interface (Recommended)

Start the FastAPI backend and Streamlit frontend:

```bash
# Terminal 1: Start the API server
cd src
uvicorn backend.api:app --reload --port 8000

# Terminal 2: Start the Streamlit frontend
cd src
streamlit run frontend/app.py
```

Then open http://localhost:8501 in your browser.

In the web interface:
1. Enter your OpenAI API key in the sidebar
2. Upload any images you want to include (optional)
3. Describe your presentation in the chat
4. Download the generated PowerPoint

### Option 2: Command Line Interface

```bash
# Using the installed command
pptx-cli

# Or run directly
python -m cli
```

For CLI usage, set your API key as an environment variable:
```bash
export OPENAI_API_KEY='your-api-key'
```

CLI commands:
- `create` - Generate a full PowerPoint presentation
- `plan` - Generate slide plan only (no PPTX)
- `catalog` - View available visualizations
- `help` - Show available commands
- `exit` - Quit the application

## Project Structure

```
powerpoint-generator/
├── configs/
│   └── config.yaml          # Runtime configuration
├── js/
│   └── html2pptx/           # HTML to PPTX converter (Node.js)
├── src/
│   ├── core/                # Shared business logic
│   │   ├── agents/          # LLM agents (orchestrator, planner, designer)
│   │   ├── prompts/         # System prompts for agents
│   │   ├── config.py        # Configuration loader
│   │   ├── models.py        # Pydantic data models
│   │   └── model_provider.py
│   ├── backend/             # FastAPI REST API
│   │   ├── api.py           # API endpoints
│   │   ├── schemas.py       # Request/response schemas
│   │   └── ...
│   ├── frontend/            # Streamlit web app
│   │   └── app.py
│   └── cli/                 # Command line interface
│       └── __main__.py
├── data/
│   └── visualisation_store/
│       ├── catalog.json     # Visualization metadata
│       └── plots/           # PNG files
├── output/                  # Generated presentations
├── sessions/                # Web session data
├── package.json             # Node.js dependencies
└── pyproject.toml           # Python package config
```

## How It Works

1. **User Input**: Describe what presentation you want
2. **Slide Planning**: AI agent plans slide structure and selects visualizations
3. **Slide Design**: Each slide is designed as HTML with proper layout
4. **PPTX Generation**: HTML slides are converted to PowerPoint format

```
User Request → Orchestrator → Slide Planner → Slide Designer → HTML → PPTX
```

## Example Prompts

- "Create a quarterly sales report for the leadership team"
- "Build a project status update with timeline and milestones"
- "Make a product launch presentation highlighting key features"
- "Summarize our marketing campaign results with charts"

## Troubleshooting

### API Key Issues
- **Web**: Enter your API key in the sidebar settings
- **CLI**: Set `OPENAI_API_KEY` environment variable or create a `.env` file

### "Converter script not found"
Ensure Node.js dependencies are installed:
```bash
npm install
```

### "Cannot connect to API server"
Make sure the backend is running on port 8000:
```bash
uvicorn backend.api:app --port 8000
```

### Slides not generating
- Check that `data/visualisation_store/catalog.json` exists
- Verify your API key is valid
- Check the console for error messages

## Development

### Running in Development Mode

```bash
# API with auto-reload
uvicorn backend.api:app --reload

# Streamlit with auto-reload (default behavior)
streamlit run frontend/app.py
```

### Project Dependencies

Python dependencies are managed in `pyproject.toml`. Node.js dependencies are in `package.json`.

## Roadmap

Future improvements planned for SlideWeaver:

- **Slide Master Templates** - Support for custom PowerPoint templates and themes
- **Enhanced Frontend UI** - Improved web interface with better UX
- **Langfuse Integration** - LLM observability and tracing for debugging and optimization
- **Multi-Provider Support** - Support for Anthropic, Google, Groq, and other LLM providers

## License

MIT
