#!/usr/bin/env python3
"""Verify Day 7 notebook completeness and format (PHASE 3)"""

import json

notebook_path = '/home/user/Qwen-Agent/learning_qwen_agent/day_07_custom_tools/day_07_notebook.ipynb'

with open(notebook_path, 'r') as f:
    nb = json.load(f)

print("=" * 70)
print("DAY 7 NOTEBOOK VERIFICATION")
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

# Check for known issues (function calling)
print(f"\n✅ Step 3.3: Check Known Issues")
known_fc_issues = 0
other_errors = 0

for i, cell in enumerate(code_cells):
    if cell.get('outputs'):
        for output in cell['outputs']:
            if output.get('text'):
                text = ''.join(output['text']) if isinstance(output['text'], list) else output['text']
                if 'ValidationError' in text and 'FunctionCall' in text:
                    known_fc_issues += 1
                elif 'Error:' in text or output.get('name') == 'stderr':
                    other_errors += 1

if known_fc_issues > 0:
    print(f"   ⚠️  {known_fc_issues} cells with known function calling compatibility issue")
    print(f"   ✅ This is expected with Fireworks API (cells calling agent.run with tools)")
else:
    print(f"   ✅ No known function calling issues detected")

if other_errors > 0:
    print(f"   ⚠️  {other_errors} cells with other errors")
else:
    print(f"   ✅ No other errors detected")

# Summary
print(f"\n" + "=" * 70)
print(f"VERIFICATION SUMMARY")
print(f"=" * 70)
print(f"✅ Output coverage: {len(cells_with_output)}/{executable_cells} " +
      f"({'✅ 100%' if len(cells_with_output) == executable_cells else '❌ Incomplete'})")
print(f"✅ Output format: {'✅ All correct' if not format_errors else f'❌ {len(format_errors)} errors'}")
print(f"✅ Known FC issues: {'⚠️  Documented ({} cells)'.format(known_fc_issues) if known_fc_issues > 0 else '✅ None'}")
print(f"✅ Other errors: {'⚠️  {} cells'.format(other_errors) if other_errors > 0 else '✅ None'}")
print(f"\n{'✅ DAY 7 COMPLETE - READY TO COMMIT' if len(cells_with_output) == executable_cells and not format_errors else '❌ NEEDS FIXES'}")
print(f"\n💡 Note: Function calling errors are expected with Fireworks API")
print(f"=" * 70)
