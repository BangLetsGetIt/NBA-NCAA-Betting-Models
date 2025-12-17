#!/bin/bash
# Run WNBA Models
echo "Starting WNBA Model Run..."

# 1. Run Spreads/Totals
python3 wnba/wnba_model.py

# 2. Run Props
python3 wnba/wnba_props_model.py

# 3. Open Results (Mac)
if [[ "$OSTYPE" == "darwin"* ]]; then
    open wnba/wnba_model_output.html
    open wnba/wnba_props_output.html
fi

echo "Done."
