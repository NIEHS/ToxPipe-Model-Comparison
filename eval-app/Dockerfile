# Use the official uv base image with Python 3.12 on Debian Bookworm slim
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set a working directory
WORKDIR /app

# Copy the metadata files first to leverage layer caching for dependency installs
COPY pyproject.toml .python-version uv.lock ./

# Install project dependencies using uv (reads uv.lock / pyproject)
RUN uv sync

# Copy the rest of the project and keep file ownership for the non-root user
COPY . .

# Expose the port the app runs on
EXPOSE 8011

# Run the Shiny app with uv; entrypoint is `app.py`
CMD ["uv", "run", "shiny", "run", "app.py", "-h", "0.0.0.0", "-p", "8011"]
