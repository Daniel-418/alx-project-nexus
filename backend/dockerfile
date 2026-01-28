# Base Image
FROM python:3.12-slim

# Set environmental variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set working directory
WORKDIR /app

# Copy project dependencies
COPY requirements.txt .

# install system dependencies
RUN apt-get update && apt-get install -y \
	postgresql-client \
	netcat-openbsd \
	&& rm -rf /var/lib/apt/lists/*

# install project dependencies
RUN pip install --no-cache-dir -r requirements.txt

# copy the rest of the code
COPY . .
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
# expose a port
EXPOSE 8000

# use gunicorn to start the server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
