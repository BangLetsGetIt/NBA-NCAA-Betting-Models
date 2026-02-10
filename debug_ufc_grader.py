
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'ufc'))
from ufc_model_runner import UFCModelRunner

print("Debugging UFC Grading...")
runner = UFCModelRunner()
print("Calling grade_pending_picks()...")
count = runner.grade_pending_picks()
print(f"Graded {count} picks.")
