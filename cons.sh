printf "\033c\033[40;37m\nwath you need from gpt?.\n"
read ax11
echo $ax11 >>gpt.log
curl "https://generativelanguage.googleapis.com/v1beta/models/${MODEL_ID}:generateContent?key=$GOOGLE_API_KEY" \
    -H 'Content-Type: application/json' \
    -X POST \
    -d '{
      "contents": [{
        "parts":[{"text": "$ax11"}]
        }]
       }' > out.txt

cat out.txt >> gpt.log
cat out.txt
