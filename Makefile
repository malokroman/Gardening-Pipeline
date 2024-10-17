init-dev:
	direnv allow
	pip install -r dev-requirements.txt
	pre-commit install
