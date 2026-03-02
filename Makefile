BRANCH := $(shell git rev-parse --abbrev-ref HEAD)

sort:
	@echo ">> Sorting imports..."
	@python3 scripts/sort_imports.py

format:
	@echo ">> Formatting with Black..."
	@black .

deploy: format sort
	@echo ">> Staging changes..."
	@git add .
	@echo ">> Committing..."
	@git commit -m "prepare for deploy"
	@echo ">> Pushing to $(BRANCH)..."
	@git push -u origin $(BRANCH)
	@echo ">> Done!"
