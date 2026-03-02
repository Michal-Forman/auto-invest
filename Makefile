sort:
	python3 scripts/sort_imports.py

deploy:
	pipreqs . --force --ignore supabase
	git add .
	git commit -m "prepare for deploy"
	git push
