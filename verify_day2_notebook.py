#!/usr/bin/env python3
"""Verify Day 2 notebook completeness and format (PHASE 3)"""

import json

notebook_path = '/home/user/Qwen-Agent/learning_qwen_agent/day_02_message_schema/day_02_notebook.ipynb'

with open(notebook_path, 'r') as f:
    nb = json.load(f)

print("=" * 70)
print("DAY 2 NOTEBOOK VERIFICATION")
print("=" * 70)

# Step 3.1: Count and Verify Outputs
code_cells = [c for c in nb['cells'] if c['cell_type'] == 'code']
cells_with_output = [c for c in code_cells if c.get('outputs')]

# Identify TODO cells (exercises) - these should not have output
todo_cells = []
for idx, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source']) if isinstance(cell['source'], list) else cell['source']
        if source.strip().startswith('# TODO'):
            todo_cells.append(idx)

# Calculate executable cells (non-TODO)
executable_cells = len(code_cells) - len(todo_cells)

print(f"\n✅ Step 3.1: Count and Verify Outputs")
print(f"   Total code cells: {len(code_cells)}")
print(f"   TODO cells (exercises): {len(todo_cells)}")
print(f"   Executable cells: {executable_cells}")
print(f"   Cells with output: {len(cells_with_output)}")

if len(cells_with_output) == executable_cells:
    print(f"   ✅ 100% coverage ({len(cells_with_output)}/{executable_cells})")
else:
    print(f"   ❌ Incomplete: {len(cells_with_output)}/{executable_cells} cells have output")
    missing = executable_cells - len(cells_with_output)
    print(f"   Missing: {missing} cells")

# Step 3.2: Verify Output Format
print(f"\n✅ Step 3.2: Verify Output Format")
format_errors = []

for i, cell in enumerate(code_cells):
    if cell.get('outputs'):
        for output in cell['outputs']:
            if output.get('text'):
                if not isinstance(output['text'], list):
                    format_errors.append((i, type(output['text']).__name__))

if not format_errors:
    print(f"   ✅ All outputs in array format")
else:
    print(f"   ❌ Format errors found:")
    for cell_idx, type_name in format_errors:
        print(f"      Cell {cell_idx}: output.text is {type_name}, should be list")

# Step 3.3: Check for accumulated garbage (the pollution issue)
print(f"\n✅ Step 3.3: Check for Output Pollution")
pollution_found = []

# Check if any cell's output contains the Fireworks API config message
# (which should only be in cell 4)
config_signature = "✅ Configured for Fireworks API"
for idx, cell in enumerate(code_cells):
    if idx == 4:
        continue  # Skip cell 4, it's supposed to have this

    if cell.get('outputs'):
        for output in cell['outputs']:
            if output.get('text'):
                text = ''.join(output['text']) if isinstance(output['text'], list) else output['text']
                if config_signature in text:
                    pollution_found.append(idx)
                    break

if pollution_found:
    print(f"   ❌ Output pollution detected in {len(pollution_found)} cells!")
    print(f"   Affected cells: {pollution_found}")
    print(f"   These cells have accumulated output from cell 4")
else:
    print(f"   ✅ No output pollution detected")
    print(f"   Each cell has only its own output")

# Summary
print(f"\n" + "=" * 70)
print(f"VERIFICATION SUMMARY")
print(f"=" * 70)
print(f"✅ Output coverage: {len(cells_with_output)}/{executable_cells} " +
      f"({'✅ 100%' if len(cells_with_output) == executable_cells else '❌ Incomplete'})")
print(f"✅ Output format: {'✅ All correct' if not format_errors else f'❌ {len(format_errors)} errors'}")
print(f"✅ Output pollution: {'❌ FOUND in {} cells'.format(len(pollution_found)) if pollution_found else '✅ None - Clean outputs'}")
print(f"\n{'✅ DAY 2 FIXED - READY TO COMMIT' if len(cells_with_output) == executable_cells and not format_errors and not pollution_found else '❌ NEEDS MORE WORK'}")
print(f"=" * 70)
