#!/data/data/com.termux/files/usr/bin/bash

STAMP=$(date +"%Y%m%d_%H%M%S")

echo "=============================="
echo "📌 Creating Git Checkpoint..."
echo "=============================="

git add .

git commit -m "Milestone 2: Trading Core Validated + 5x Margin Display"

echo
echo "=============================="
echo "📦 Creating Android Backup..."
echo "=============================="

ZIPFILE="/storage/emulated/0/Download/TradingCore_Validated_02_${STAMP}.zip"

zip -r "$ZIPFILE" . \
-x ".git/*" \
"__pycache__/*" \
"*.pyc" \
"*.pyo" \
"logs/*" \
"reports/*" \
"*.log" \
"*.csv" \
"*.db" \
"*.sqlite*" \
"*.zip" \
"*.tar" \
"*.gz"

echo
echo "=============================="
echo "✅ CHECKPOINT COMPLETE"
echo "=============================="

git log --oneline -1

echo

ls -lh "$ZIPFILE"

echo

echo "📁 Backup Location:"
echo "$ZIPFILE"
