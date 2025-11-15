FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copy dependency metadata first for better caching
COPY pyproject.toml uv.lock /app/

# Convert the pyproject dependency list into a temporary requirements file
RUN python - <<'PY'
import pathlib, tomllib
pyproject = tomllib.loads(pathlib.Path('pyproject.toml').read_text())
requirements = pyproject.get('project', {}).get('dependencies', [])
pathlib.Path('requirements.txt').write_text('\n'.join(requirements))
PY

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy the rest of the project
COPY . /app

EXPOSE 8050

CMD ["python", "main.py"]
