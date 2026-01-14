from __future__ import annotations

import json
import tempfile
from pathlib import Path

from src.utils.subprocess_tools import run_command


def render_html_to_pptx(
    *,
    html_files: list[Path],
    output_pptx: Path,
    js_workspace: Path,
    html2pptx_js: Path,
    layout: str = "LAYOUT_16x9",
) -> tuple[int, str, str]:
    """Render HTML slides into a PPTX using the local Node workspace.

    Returns: (returncode, stdout, stderr)
    """

    node_modules = js_workspace / "node_modules"
    if not (js_workspace / "package.json").exists():
        raise FileNotFoundError(
            f"Missing Node workspace package.json at {js_workspace}"
        )
    if not node_modules.exists():
        raise FileNotFoundError(
            f"Missing node_modules at {node_modules}. Run: (cd {js_workspace} && npm "
            "install)"
        )

    output_pptx.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        driver = tmp_dir / "driver.mjs"
        driver_code = f"""
import {{ createRequire }} from 'module';
import {{ fileURLToPath }} from 'url';
import {{ dirname, join }} from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const require = createRequire(import.meta.url);

// Use absolute paths to ensure modules are found
const pptxgen = require('{str((node_modules / "pptxgenjs").resolve())}');
const html2pptx = require(process.env.HTML2PPTX_JS);

async function main() {{
  const pptx = new pptxgen();
  pptx.layout = process.env.PPTX_LAYOUT;

  const htmlFiles = JSON.parse(process.env.HTML_FILES_JSON);
  for (const f of htmlFiles) {{
    await html2pptx(f, pptx);
  }}

  await pptx.writeFile({{ fileName: process.env.OUTPUT_PPTX }});
}}

main().catch((err) => {{
  console.error(String(err && err.stack ? err.stack : err));
  process.exit(1);
}});
"""
        driver.write_text(driver_code.lstrip(), encoding="utf-8")

        env = {
            "HTML2PPTX_JS": str(html2pptx_js.resolve()),
            "PPTX_LAYOUT": layout,
            "HTML_FILES_JSON": json.dumps([str(p.resolve()) for p in html_files]),
            "OUTPUT_PPTX": str(output_pptx.resolve()),
            "NODE_PATH": str(node_modules.resolve()),
        }

        res = run_command(
            ["node", str(driver)], cwd=js_workspace, env=env, timeout_s=900
        )
        return res.returncode, res.stdout, res.stderr
