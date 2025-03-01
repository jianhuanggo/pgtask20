FROM public.ecr.aws/lambda/python:3.11

# Set working directory
WORKDIR /var/task

# Copy requirements file
COPY app/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy function code
COPY app/lambda_function/ .

# Set the CMD to your handler
CMD [ "app.handler" ]
