FROM public.ecr.aws/lambda/python:3.11

# Copy requirements first (caches better)
COPY requirements.txt .

# Install dependencies into Lambda task root
RUN pip install --no-cache-dir -r requirements.txt --target /var/task

# Copy your source code
COPY agent_cli/ ./agent_cli/

# Set the Lambda handler
CMD [ "agent_cli.lambda_handler.handler" ]
