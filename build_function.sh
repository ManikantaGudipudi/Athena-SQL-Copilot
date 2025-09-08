#!/bin/bash
set -e

FUNC_DIR="function"
ZIP_FILE="query_api_lambda.zip"

# Clean old builds
rm -rf $FUNC_DIR $ZIP_FILE
mkdir -p $FUNC_DIR

echo "📦 Packaging Query API Lambda function..."

# Copy only your app code into build dir
cp -r query_api $FUNC_DIR/

# Create zip
cd $FUNC_DIR
zip -r9 ../$ZIP_FILE .
cd ..

# Cleanup build dir
rm -rf $FUNC_DIR

echo "✅ Function package ready: $ZIP_FILE"
echo "   Upload this to your Lambda function in the AWS Console."
