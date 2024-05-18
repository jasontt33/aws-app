# Use an official Python runtime as a parent image
FROM  python:3-slim 

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
#RUN pip install gunicorn

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Run the Flask app using gunicorn with the specified number of workers
CMD ["python", "app.py"]

