sort:
	python3 scripts/sort_imports.py

format:
	black .

requirements:
	pipreqs . --force --ignore supabase,scripts
	grep -qxF 'python-dotenv==1.2.2' requirements.txt || echo 'python-dotenv==1.2.2' >> requirements.txt
	grep -qxF 'requests==2.32.5' requirements.txt || echo 'requests==2.32.5' >> requirements.txt

BRANCH := $(shell git rev-parse --abbrev-ref HEAD)

deploy: sort format requirements
	git add .
	git commit -m "prepare for deploy"
	git push -u origin $(BRANCH)
