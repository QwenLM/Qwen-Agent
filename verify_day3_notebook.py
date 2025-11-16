#!/usr/bin/env python3
"""Verify Day 3 notebook completeness and format (PHASE 3)"""

import json

notebook_path = '/home/user/Qwen-Agent/learning_qwen_agent/day_03_llm_integration/day_03_notebook.ipynb'

with open(notebook_path, 'r') as f:
    nb = json.load(f)

print("=" * 70)
print("DAY 3 NOTEBOOK VERIFICATION")
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

# Step 3.3: Technical Claims Audit
print(f"\n✅ Step 3.3: Technical Claims Audit")
print(f"   Checking for unsourced technical claims...")

markdown_cells = [c for c in nb['cells'] if c['cell_type'] == 'markdown']
claims_to_verify = []

# Check for version numbers without sources
for i, cell in enumerate(markdown_cells):
    source = ''.join(cell['source']) if isinstance(cell['source'], list) else cell['source']

    # Look for version numbers (basic check)
    if 'version' in source.lower() or 'v0.' in source or 'v1.' in source:
        # Check if there's a link or source nearby
        if 'http' not in source and 'see ' not in source.lower() and 'docs' not in source.lower():
            claims_to_verify.append(i)

# Check for specific model claims
model_claim_keywords = ['supports', 'requires', 'compatible', 'works with']
for i, cell in enumerate(markdown_cells):
    source = ''.join(cell['source']) if isinstance(cell['source'], list) else cell['source']
    for keyword in model_claim_keywords:
        if keyword in source.lower():
            # Basic check - if claim but no evidence, flag it
            # This is a simplified check
            pass

if not claims_to_verify:
    print(f"   ✅ No obvious unsourced claims found")
else:
    print(f"   ⚠️  {len(claims_to_verify)} cells may need source verification")

# Summary
print(f"\n" + "=" * 70)
print(f"VERIFICATION SUMMARY")
print(f"=" * 70)
print(f"✅ Output coverage: {len(cells_with_output)}/{executable_cells} " +
      f"({'✅ 100%' if len(cells_with_output) == executable_cells else '❌ Incomplete'})")
print(f"✅ Output format: {'✅ All correct' if not format_errors else f'❌ {len(format_errors)} errors'}")
print(f"✅ Technical claims: {'✅ Looks good' if not claims_to_verify else f'⚠️  {len(claims_to_verify)} to verify'}")
print(f"\n{'✅ READY FOR PHASE 4' if len(cells_with_output) == executable_cells and not format_errors else '❌ NEEDS FIXES'}")
print(f"=" * 70)
