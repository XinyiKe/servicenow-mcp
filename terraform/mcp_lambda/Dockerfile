# Use the official AWS Lambda Python 3.13 base image
FROM public.ecr.aws/lambda/python:3.13

# Set working directory
WORKDIR /var/task

# Copy dependencies list
COPY requirements.txt .

# Install them into /var/task
RUN pip install --upgrade pip && pip install -r requirements.txt -t .

# Copy source code (lambda function + client)
COPY lambda_function.py .
COPY basic_mcp_client.py .

# Set the handler
CMD ["lambda_function.lambda_handler"]



