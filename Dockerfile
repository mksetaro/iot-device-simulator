FROM python:3.8.10

ADD . /workspace

RUN pip install -e /workspace

CMD ["python", "/workspace/iotsim/src/app.py"]