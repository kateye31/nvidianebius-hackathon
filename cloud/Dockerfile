FROM python:3.11-slim
WORKDIR /srv
COPY cloud/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY cloud/app ./app
COPY dashboard ./dashboard
ENV DASHBOARD_DIR=/srv/dashboard
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
