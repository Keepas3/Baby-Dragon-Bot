# 1. Start with your required Python version
FROM python:3.11-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy only requirements first (leverages Docker cache)
COPY requirements.txt .

# 4. Install your Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Tell Playwright to download Chromium AND its OS-level system dependencies
RUN playwright install --with-deps chromium

# 6. Copy the rest of your bot's files
COPY . .

# 7. Set your PYTHONPATH
ENV PYTHONPATH="/app:/app/src"

# 8. Fire up the engine
CMD ["python", "src/main.py"]