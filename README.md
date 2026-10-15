# Duly Chat Backend

[![Checks](https://github.com/duly-app/duly-chat-backend/actions/workflows/pr-checks.yml/badge.svg?branch=main)](https://github.com/duly-app/duly-chat-backend/actions/workflows/pr-checks.yml)
[![Coverage](https://raw.githubusercontent.com/duly-app/duly-chat-backend/python-coverage-comment-action-data/badge.svg)](https://github.com/duly-app/duly-chat-backend/tree/python-coverage-comment-action-data)

This repository is the chatbot backend of the Duly app. It runs on FastAPI.

## Getting Started
Package installation and version control is handled with Poetry. To install dependencies and enter the virtual environment
```bash
poetry install
eval $(poetry env activate)
```

To get started locally, just run
```bash
fastapi dev src/app.py
```

The server listens on port 8000. Interactive API documentation is generated from the routes and served at `/docs`.

Alternatively, build and run the development image
```bash
docker build -f Dockerfile.dev -t duly-chat-backend:dev .
docker run -p 8000:8000 duly-chat-backend:dev
```

## CI
Continuous integration on GitHub actions can be mimicked locally with `tox`. Install `tox` with `pipx`

```bash
pipx install tox
```

then from the root of the project run
```bash
tox
```

If tests related to linting or formatting are failing, it is recommended to use the associated tools. Therefore, install `black`, `isort`, `iflake`, `autoflake`, `mypy` with `pipx` and use them accordingly.
