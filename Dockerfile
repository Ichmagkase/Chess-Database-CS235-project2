FROM python:3.14.3-alpine3.23
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY ./src ./src
WORKDIR ./src
CMD ["python", "main.py"]

