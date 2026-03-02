sort:
	python3 scripts/sort_imports.py main.py coinmate.py executor.py instruments.py instrument_data.py log.py settings.py trading212.py utils.py db/client.py db/orders.py db/runs.py

deploy:
	pipreqs . --force --ignore supabase
	git add .
	git commit -m "prepare for deploy"
	git push
