# Image for the Nebius Serverless Job
FROM python:3.11-slim
WORKDIR /job
COPY sim ./sim
ENTRYPOINT ["python", "sim/outage_sim.py"]
