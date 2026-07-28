FROM python:3.12-slim AS voices
RUN pip install --no-cache-dir piper-tts && \
    python3 -m piper.download_voices fr_FR-siwis-medium --data-dir /voices

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY --from=voices /voices /models
ENV PORT=8000
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
