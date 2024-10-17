init-dev:
	direnv allow
	pip install -r dev-requirements.txt -r requirements.txt
	pre-commit install
