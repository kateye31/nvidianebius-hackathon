# Image for the Nebius Serverless Job. Pick the script with the job's args, e.g.
#   sim/outage_sim.py --homes 2000 --med-share X --elderly-share Y
#   sim/hubs.py --zip 33956 --judge
#   sim/predict/train.py        (mount data/ with the fetched raw files)
FROM python:3.11-slim
WORKDIR /job
COPY sim/requirements.txt ./sim/requirements.txt
RUN pip install --no-cache-dir -r sim/requirements.txt
COPY sim ./sim
COPY data/*.py ./data/
COPY cloud/app/heat.py ./cloud/app/heat.py
RUN touch cloud/app/__init__.py
ENTRYPOINT ["python"]
CMD ["sim/outage_sim.py", "--help"]
