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
RUN python3 -c '\
import streamlit\n\
import os\n\
p = os.path.join(os.path.dirname(streamlit.__file__), "static", "index.html")\n\
with open(p, "r") as f: html = f.read()\n\
html = html.replace("<title>Streamlit</title>", "<title>Lead Manager</title>")\n\
html = html.replace("favicon.png", "favicon.png?v=5")\n\
script = """<script>\n\
    const observer = new MutationObserver((mutations) => {\n\
        if (document.title !== "Lead Manager") document.title = "Lead Manager";\n\
        let link = document.querySelector("link[rel*=\\x27icon\\x27]");\n\
        if (link && link.href !== "./favicon.png?v=5") {\n\
            link.href = "./favicon.png?v=5";\n\
        }\n\
    });\n\
    observer.observe(document.documentElement, { childList: true, subtree: true, attributes: true });\n\
    setTimeout(() => observer.disconnect(), 5000);\n\
</script>"""\n\
if "MutationObserver" not in html: html = html.replace("<head>", "<head>" + script)\n\
with open(p, "w") as f: f.write(html)\n\
' && cp frontend_app/2.png.jpeg $(python3 -c "import streamlit; import os; print(os.path.dirname(streamlit.__file__))")/static/favicon.png

# Create a data directory for the persistent database and set permissions
RUN mkdir -p /app/data && chmod -R 777 /app/data

# Set environment variables
ENV PYTHONPATH=/app/backend
ENV PYTHONUNBUFFERED=1

# The actual command will be handled by docker-compose
CMD ["python3"]
