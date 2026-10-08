FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends g++ && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml .
COPY usquant usquant
RUN pip install --no-cache-dir '.[mysql]'
COPY cpp cpp
COPY scripts scripts
COPY config config
COPY tests tests
RUN python scripts/build_cpp.py && python -m unittest discover -s tests -v
ENTRYPOINT ["python", "-m", "usquant"]
CMD ["demo", "--backend", "mysql", "--native"]
