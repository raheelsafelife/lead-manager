# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Robust pip installation
RUN pip3 install --no-cache-dir --upgrade pip
RUN pip3 install --no-cache-dir --default-timeout=100 -r requirements.txt

# Copy the rest of the application code
COPY . .

# Patch Streamlit Branding (Deep Fix to eliminate flash)
RUN python3 -c 'import streamlit; import os; p = os.path.join(os.path.dirname(streamlit.__file__), "static", "index.html"); html = open(p).read(); html = html.replace("<title>Streamlit</title>", "<title>Lead Manager</title>"); html = html.replace("favicon.png", "favicon.png?v=10"); script = "<script>const force = () => { if (document.title !== \"Lead Manager\") document.title = \"Lead Manager\"; document.querySelectorAll(\"link[rel*=\\\"icon\\\"]\").forEach(l => { if (!l.href.includes(\"favicon.png?v=10\")) l.href = \"./favicon.png?v=10\"; }); }; force(); const obs = new MutationObserver(force); obs.observe(document.documentElement, { childList: true, subtree: true, attributes: true }); </script>"; html = html.replace("<head>", "<head>" + script) if "MutationObserver" not in html else html; open(p, "w").write(html)' && \
    cp frontend_app/2.png.jpeg $(python3 -c "import streamlit; import os; print(os.path.dirname(streamlit.__file__))")/static/favicon.png && \
    cp frontend_app/2.png.jpeg $(python3 -c "import streamlit; import os; print(os.path.dirname(streamlit.__file__))")/static/favicon.ico

# Create a data directory for the persistent database and set permissions
RUN mkdir -p /app/data && chmod -R 777 /app/data

# Set environment variables
ENV PYTHONPATH=/app/backend
ENV PYTHONUNBUFFERED=1

# The actual command will be handled by docker-compose
CMD ["python3"]
