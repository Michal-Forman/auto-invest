BRANCH := $(shell git rev-parse --abbrev-ref HEAD)

sort:
	@echo ">> Sorting imports..."
	@python3 scripts/sort_imports.py

format:
	@echo ">> Formatting with Black..."
	@black .

typecheck:
	@echo ">> Type checking with mypy..."
	@python3 -m mypy --explicit-package-bases *.py db/*.py

deploy: format sort typecheck
	@echo ">> Staging changes..."
	@git add .
	@echo ">> Committing..."
	@git commit -m "prepare for deploy"
	@echo ">> Pushing to $(BRANCH)..."
	@git push -u origin $(BRANCH)
	@echo ">> Done!"
