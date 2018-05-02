# FROM python:3.6
# COPY . /bubbles
# WORKDIR /bubbles
# RUN pip install --no-cache-dir pipenv
# RUN PIP_NO_CACHE_DIR=false pipenv install --dev
# EXPOSE 80
# ENV FLASK_APP /bubbles/app.py
# ENV FLASK_DEBUG 1
# CMD pipenv run python -m flask run --port 80

FROM tiangolo/uwsgi-nginx-flask:python3.6

COPY . /app
WORKDIR /app
RUN pip install --no-cache-dir pipenv
RUN PIP_NO_CACHE_DIR=false pipenv install --dev --system

