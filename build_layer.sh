#!/bin/bash
set -e

LAYER_DIR="layer"
PYTHON_VERSION="3.11"
DOCKER_IMAGE="public.ecr.aws/lambda/python:${PYTHON_VERSION}"

# Clean old builds
rm -rf $LAYER_DIR layer.zip
mkdir -p $LAYER_DIR/python

echo "🚀 Building Lambda Layer using $DOCKER_IMAGE ..."

# Run inside Amazon Linux (Lambda runtime) container
docker run --rm -v "$PWD":/var/task --entrypoint /bin/bash $DOCKER_IMAGE -c "
  pip install \
    fastapi \
    mangum \
    pydantic \
    boto3 \
    requests \
    --target /var/task/$LAYER_DIR/python --upgrade
"

# Package into zip
cd $LAYER_DIR
zip -r9 ../layer.zip python
cd ..

echo "✅ Build complete: layer.zip is ready for upload to AWS Lambda"
