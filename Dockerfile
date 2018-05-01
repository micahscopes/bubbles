FROM python
RUN pip install pipenv
RUN pipenv install --dev
