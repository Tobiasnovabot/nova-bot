#!/bin/bash

REPO_DIR="/home/nova/nova-bot"
cd "$REPO_DIR" || exit 1

# 1. Split store filer (>2GB) i hele mappen
find . -type f -size +2000M | while read F; do
  echo "Splitter $F ..."
  split -b 1900M "$F" "${F}.part_"
  if [ $? -eq 0 ]; then
    echo "Sletter original: $F"
    rm "$F"
  else
    echo "Split feilet på $F – originalen beholdes!"
  fi
done

# 2. Legg til alle filer i git
git add .

# 3. Commit endringer
git commit -m "Automatisk push: splitter store filer og pusher alt"

# 4. Push til GitHub
git push origin main
