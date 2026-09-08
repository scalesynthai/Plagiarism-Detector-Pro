.PHONY: help install test run run-prod docker-build docker-run clean

help:
	@echo "Plagiarism Detector Pro - Developer Commands"
	@echo "------------------------------------------------"
	@echo "make install      : Install production & dev dependencies"
	@echo "make test         : Run automated test suite"
	@echo "make run          : Run local development server"
	@echo "make run-prod     : Run production Gunicorn WSGI server"
	@echo "make docker-build : Build production Docker image"
	@echo "make docker-run   : Run application in Docker container"
	@echo "make clean        : Remove Python caches and temporary files"

install:
	pip install -r requirements.txt

test:
	python -m unittest discover tests

run:
	python app.py

run-prod:
	gunicorn wsgi:app -b 0.0.0.0:5001 --workers 4

docker-build:
	docker build -t scalesynthai/plagiarism-detector-pro:latest .

docker-run:
	docker compose up -d

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".DS_Store" -delete
