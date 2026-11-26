import subprocess
import sys
res = subprocess.run(['pytest', 'projects/01_python_fundamentals/tests'])
sys.exit(res.returncode)
