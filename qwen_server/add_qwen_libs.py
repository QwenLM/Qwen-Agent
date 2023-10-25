import sys
from pathlib import Path

# A temporary solution. We should use `python setup.py develop` in the future.
sys.path.insert(0, str(Path(__file__).absolute().parent.parent))
