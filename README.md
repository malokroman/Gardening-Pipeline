# Gardening-Pipeline
An open-source data collection pipeline for gardening

## Technology

This data pipeline uses:
- Dagster (Data Orchestrator)
- Terraform (IaC)
- Scrapy (Web Scrapping)

These code quality tools are also employed:
- pre-commit
- ruff

Virtual Environment management:
- pyenv
- direnv

## Development

Before you start the development, you will need `direnv` and `pyenv` installed and configured. Alternatively, you can manually create a virtual environment and remove the line `direnv allow` from Makefile.

To initialise the development environment, simply run `make init-dev`
