FROM pytorch/pytorch:2.11.0-cuda12.8-cudnn9-runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /opt/vast-benchmarking
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --break-system-packages --no-cache-dir .

VOLUME ["/results"]
EXPOSE 8080

ENTRYPOINT ["vast-benchmark"]
CMD ["run", "--db", "/results/benchmarks.sqlite", "--output", "/results/latest.json"]
