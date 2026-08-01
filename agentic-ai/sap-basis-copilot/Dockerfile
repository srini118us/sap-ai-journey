FROM python:3.12-slim

WORKDIR /app

RUN pip install google-adk google-cloud-storage google-cloud-aiplatform paramiko google-cloud-secret-manager google-cloud-os-config google-cloud-compute

COPY sap_basis_copilot/ ./sap_basis_copilot/
COPY sap_basis_copilot/.env .env

ENV GOOGLE_CLOUD_PROJECT=sap-basis-copilot
ENV GOOGLE_CLOUD_LOCATION=global
ENV GOOGLE_GENAI_USE_VERTEXAI=TRUE

EXPOSE 8000

CMD ["adk", "web", "--host", "0.0.0.0", "--port", "8000"]
