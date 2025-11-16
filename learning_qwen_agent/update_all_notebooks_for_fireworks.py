#!/usr/bin/env python3
"""
Auto-update all Qwen-Agent learning notebooks to use Fireworks API
instead of DashScope.

Usage: python3 update_all_notebooks_for_fireworks.py
"""

import json
import os
from pathlib import Path

# Fireworks configuration template
FIREWORKS_CONFIG_CELL = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# ================================================\n",
        "# FIREWORKS API CONFIGURATION\n",
        "# ================================================\n",
        "import os\n",
        "\n",
        "# Set API credentials\n",
        "os.environ['FIREWORKS_API_KEY'] = 'fw_3ZTLPrnEtuscTUPYy3sYx3ag'\n",
        "\n",
        "# Standard configuration for Fireworks Qwen3-235B-A22B-Thinking\n",
        "llm_cfg_fireworks = {\n",
        "    'model': 'accounts/fireworks/models/qwen3-235b-a22b-thinking-2507',\n",
        "    'model_server': 'https://api.fireworks.ai/inference/v1',\n",
        "    'api_key': os.environ['FIREWORKS_API_KEY'],\n",
        "    'generate_cfg': {\n",
        "        'max_tokens': 32768,\n",
        "        'temperature': 0.6,\n",
        "    }\n",
        "}\n",
        "\n",
        "# Use this as default llm_cfg\n",
        "llm_cfg = llm_cfg_fireworks\n",
        "\n",
        "print('✅ Configured for Fireworks API')\n",
        "print(f'   Model: Qwen3-235B-A22B-Thinking-2507')\n",
        "print(f'   Max tokens: 32,768')\n"
    ]
}

def update_notebook(notebook_path):
    """Update a single notebook with Fireworks configuration"""

    print(f"Processing: {notebook_path}")

    try:
        with open(notebook_path, 'r') as f:
            nb = json.load(f)

        cells = nb.get('cells', [])
        if not cells:
            print(f"  ⚠️  No cells found")
            return False

        # Check if already has Fireworks config
        has_fireworks = any(
            'FIREWORKS API CONFIGURATION' in ''.join(cell.get('source', []))
            for cell in cells if cell.get('cell_type') == 'code'
        )

        if has_fireworks:
            print(f"  ✅ Already has Fireworks config")
            return False

        # Find first code cell
        first_code_idx = None
        for i, cell in enumerate(cells):
            if cell.get('cell_type') == 'code':
                first_code_idx = i
                break

        if first_code_idx is None:
            print(f"  ⚠️  No code cells found")
            return False

        # Insert Fireworks config before first code cell
        cells.insert(first_code_idx, FIREWORKS_CONFIG_CELL)
        nb['cells'] = cells

        # Save updated notebook
        with open(notebook_path, 'w') as f:
            json.dump(nb, f, indent=1)

        print(f"  ✅ Updated successfully")
        return True

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def main():
    """Update all notebooks in the learning curriculum"""

    base_path = Path(__file__).parent

    notebooks = [
        "day_01_prerequisites/day_01_notebook.ipynb",
        "day_02_message_schema/day_02_notebook.ipynb",
        "day_03_llm_integration/day_03_notebook.ipynb",
        "day_04_built_in_tools/day_04_notebook.ipynb",
        "day_05_first_agent/day_05_notebook.ipynb",
        "day_06_function_calling/day_06_notebook.ipynb",
        "day_07_custom_tools/day_07_notebook.ipynb",
        "day_08_assistant_agent/day_08_notebook.ipynb",
        "day_09_rag_systems/day_09_notebook.ipynb",
        "day_10_multi_agent/day_10_notebook.ipynb",
        "day_11_advanced_patterns/day_11_notebook.ipynb",
        "day_12_gui_development/day_12_notebook.ipynb",
    ]

    print("=" * 80)
    print("QWEN-AGENT NOTEBOOKS - FIREWORKS API AUTO-UPDATE")
    print("=" * 80)
    print()

    updated_count = 0
    skipped_count = 0
    error_count = 0

    for notebook_rel_path in notebooks:
        notebook_path = base_path / notebook_rel_path

        if not notebook_path.exists():
            print(f"❌ Not found: {notebook_rel_path}")
            error_count += 1
            continue

        result = update_notebook(notebook_path)

        if result:
            updated_count += 1
        elif result is False:
            skipped_count += 1
        else:
            error_count += 1

    print()
    print("=" * 80)
    print("UPDATE SUMMARY")
    print("=" * 80)
    print(f"✅ Updated: {updated_count}")
    print(f"⏭️  Skipped: {skipped_count} (already configured)")
    print(f"❌ Errors: {error_count}")
    print()

    if updated_count > 0:
        print("Next steps:")
        print("1. Review updated notebooks")
        print("2. Test with: jupyter notebook")
        print("3. Commit changes: git add . && git commit -m 'Update for Fireworks API'")

    print("=" * 80)

if __name__ == '__main__':
    main()
