#!/usr/bin/env python3
"""Execute all code cells in Day 4 notebook and save outputs"""

import json
import sys
import os
from io import StringIO
import contextlib

# Add parent directory to path
sys.path.insert(0, '/home/user/Qwen-Agent')

# Read notebook
notebook_path = '/home/user/Qwen-Agent/learning_qwen_agent/day_04_built_in_tools/day_04_notebook.ipynb'
with open(notebook_path, 'r') as f:
    nb = json.load(f)

# Global execution context (to maintain state between cells)
exec_globals = {}

def execute_cell(cell_source):
    """Execute cell code and capture output"""
    output_buffer = StringIO()

    try:
        with contextlib.redirect_stdout(output_buffer):
            exec(cell_source, exec_globals)

        output = output_buffer.getvalue()
        if output:
            # Convert to array format for Jupyter
            lines = output.rstrip('\n').split('\n')
            lines_array = [line + '\n' for line in lines[:-1]]
            if lines[-1]:
                lines_array.append(lines[-1])
            return lines_array, None
        else:
            return ['(No output)\n'], None

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        return None, [error_msg + '\n']

# Cells to execute (excluding TODOs at indices 41, 43, 45, 47)
cells_to_execute = [2, 5, 7, 10, 12, 14, 16, 18, 21, 23, 25, 27, 29, 31, 34, 36, 38]

print(f"Executing {len(cells_to_execute)} code cells...")
print("=" * 60)

executed = 0
failed = 0

for cell_idx in cells_to_execute:
    cell = nb['cells'][cell_idx]

    if cell['cell_type'] != 'code':
        continue

    # Get cell source
    source = ''.join(cell['source']) if isinstance(cell['source'], list) else cell['source']

    # Show which cell we're executing
    first_line = source.split('\n')[0][:60]
    print(f"\n[Cell {cell_idx}] {first_line}...")

    # Execute
    output_lines, error_lines = execute_cell(source)

    if error_lines:
        print(f"  ❌ Error: {error_lines[0].strip()}")
        # Save error as output
        cell['outputs'] = [{
            'output_type': 'stream',
            'name': 'stderr',
            'text': error_lines
        }]
        failed += 1
    else:
        # Show first few lines of output
        preview = ''.join(output_lines[:3]).strip()
        if len(preview) > 80:
            preview = preview[:80] + '...'
        print(f"  ✅ {preview}")

        # Save output
        cell['outputs'] = [{
            'output_type': 'stream',
            'name': 'stdout',
            'text': output_lines
        }]
        executed += 1

print("\n" + "=" * 60)
print(f"Summary: {executed} succeeded, {failed} failed")

# Write back to notebook
with open(notebook_path, 'w') as f:
    json.dump(nb, f, indent=2)

print(f"✅ Notebook saved: {notebook_path}")
