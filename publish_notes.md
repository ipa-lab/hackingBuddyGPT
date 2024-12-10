# how to publish to pypi

## start with testing if the project builds and tag the version

```bash
python -m venv venv
source venv/bin/activate
pip install -e .
pytest
git tag v0.3.0
git push origin v0.3.0
```

## build and new package

(according to https://packaging.python.org/en/latest/tutorials/packaging-projects/)

```bash
pip install build twine
python3 -m build
vi ~/.pypirc
twine check dist/*
```

Now, for next time.. test install the package in a new vanilla environment, then..

```bash
twine upload dist/*
```

## repo todos

- rebase development upon main
- bump the pyproject version number to a new `-dev` 