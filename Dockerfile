# 1. Use a standard Python image
FROM python:3.11-slim

# 2. Set the working directory INSIDE the container to the Root
WORKDIR /app

# 3. Copy the requirements file from Root to the container
COPY requirements.txt .

# 4. Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy everything from your local folder to the container
COPY . .

# 6. Set the Python path so it can find your modules inside DragonFolder
ENV PYTHONPATH="${PYTHONPATH}:/app/DragonFolder"

# 7. Run the bot (pointing to main.py inside DragonFolder)
CMD ["python", "DragonFolder/main.py"]