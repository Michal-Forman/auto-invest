BRANCH := $(shell git rev-parse --abbrev-ref HEAD)

sort:
	@echo ">> Sorting imports..."
	@python3 scripts/sort_imports.py

format:
	@echo ">> Formatting with Black..."
	@black .

requirements:
	@echo ">> Updating requirements.txt..."
	@pipreqs . --force --ignore supabase,scripts
	@grep -qxF 'python-dotenv==1.2.2' requirements.txt || echo 'python-dotenv==1.2.2' >> requirements.txt
	@grep -qxF 'requests==2.32.5' requirements.txt || echo 'requests==2.32.5' >> requirements.txt

deploy: sort format requirements
	@echo ">> Staging changes..."
	@git add .
	@echo ">> Committing..."
	@git commit -m "prepare for deploy"
	@echo ">> Pushing to $(BRANCH)..."
	@git push -u origin $(BRANCH)
	@echo ">> Done!"
