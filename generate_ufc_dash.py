
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'ufc'))
from ufc_model_runner import UFCModelRunner

print("Force generating UFC dashboard...")
runner = UFCModelRunner()
runner.generate_dashboard()
print("Done!")
