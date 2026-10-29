# Image for the Nebius Serverless Job. Pick the script with the job's args, e.g.
#   sim/outage_sim.py --homes 2000 --med-share X --elderly-share Y
#   sim/hubs.py --med-share X --elderly-share Y --judge
FROM python:3.11-slim
WORKDIR /job
RUN pip install --no-cache-dir openai==1.51.0
COPY sim ./sim
COPY cloud/app/heat.py ./cloud/app/heat.py
RUN touch cloud/app/__init__.py
ENTRYPOINT ["python"]
CMD ["sim/outage_sim.py", "--help"]
