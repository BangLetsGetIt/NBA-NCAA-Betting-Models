#!/bin/bash

# Define the aliases
ALIAS1="alias check1='cd /Users/rico/Dev/sports-models && python3 auto_grader.py --grade-only'"
ALIAS2="alias check2='cd /Users/rico/Dev/sports-models && bash run_all_models.sh'"

# Target file
RC_FILE="$HOME/.zshrc"

# Check if aliases already exist
if grep -q "alias check1=" "$RC_FILE"; then
    echo "Alias 'check1' already exists in $RC_FILE. Skipping..."
else
    echo "" >> "$RC_FILE"
    echo "# Sports Models Aliases" >> "$RC_FILE"
    echo "$ALIAS1" >> "$RC_FILE"
    echo "Added alias 'check1'"
fi

if grep -q "alias check2=" "$RC_FILE"; then
    echo "Alias 'check2' already exists in $RC_FILE. Skipping..."
else
    echo "$ALIAS2" >> "$RC_FILE"
    echo "Added alias 'check2'"
fi

echo "All done! Run 'source ~/.zshrc' to apply changes."
