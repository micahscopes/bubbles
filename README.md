This is a slack bot, so you will need a slack bot API key.  This also needs to be available at a location with https.

## Development
Make sure you have [pipenv installed](https://docs.pipenv.org/#install-pipenv-today)
```
python3 -m venv .venv
pipenv --venv
pipenv install --dev
```
To activate the virtual environment:
```
pipenv shell
```

## Running tests
Run all tests in the `./tests` directory:
```
pytest
```

To use `ipdb` breakpoints in tests, run your tests with `-s`:
```
pytest -s
```

To run `pytest-watch` on a specific test file, also enabling breakpoints:
```
ptw tests/test_bubbles.py -- -s
```


## Production
First:
```
docker pull micahscopes/bubbles
```

Then, to expose this application at port 9876 on your host, you could do:
```
docker run --name bubbles -e "BUBBLES_BOT_TOKEN='xoxb-123456789999-ABC123ABC123ABC123ABC123'" -p 9876:8080 micahscopes/bubbles
```
