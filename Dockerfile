FROM python:3.6
COPY . /bubbles
WORKDIR /bubbles
RUN pip install --no-cache-dir pipenv
RUN PIP_NO_CACHE_DIR=false pipenv install --dev
EXPOSE 8080
ENV FLASK_APP /bubbles/main.py
ENV FLASK_DEBUG 0
CMD pipenv run python -m flask run --port 8080 --host 0.0.0.0
