BRANCH := $(shell git rev-parse --abbrev-ref HEAD)

sort:
	@echo ">> Sorting imports..."
	@python3 scripts/sort_imports.py

format:
	@echo ">> Formatting with Black..."
	@black .

typecheck:
	@echo ">> Type checking with mypy..."
	@python3 -m mypy . --explicit-package-bases

test: typecheck test-unit test-integration

test-unit:
	@echo ">> Running unit tests..."
	@python3 -m pytest tests/unit/

test-integration:
	@echo ">> Running integration tests..."
	@python3 -m pytest tests/integration/ -v

deploy: format sort test
	@echo ">> Staging changes..."
	@git add .
	@echo ">> Committing..."
	@git commit -m "prepare for deploy"
	@echo ">> Pushing to $(BRANCH)..."
	@git push -u origin $(BRANCH)
	@echo ">> Done!"
