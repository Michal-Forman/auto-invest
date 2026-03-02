sort:
	python3 scripts/sort_imports.py

format:
	black .

deploy: sort format
	pipreqs . --force --ignore supabase
	git add .
	git commit -m "prepare for deploy"
	git push
