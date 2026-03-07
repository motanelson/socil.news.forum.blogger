#!/bin/bash

# Clear screen and set colors
printf "\033c\033[40;37m\nWhat do you need from Gemini?\n"
# Debug: Check if the key is set (don't do this on a public screen!)
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "Error: GOOGLE_API_KEY is not set."
    exit 1
fi
# Read user input
read a

# Log the prompt
echo "Prompt: $a" >> gpt.log

# Execute the API call
# Note: Using a heredoc or double quotes to allow variable expansion
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=$GOOGLE_API_KEY" \
    -H 'Content-Type: application/json' \
    -X POST \
    -d "{
        \"contents\": [{
            \"parts\":[{\"text\": \"$a\"}]
        }]
    }" > out.txt

# Log and display the output
cat out.txt >> gpt.log
cat out.txt