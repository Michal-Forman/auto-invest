deploy:
	pipreqs . --force --ignore supabase
	git add .
	git commit -m "prepare for deploy"
	git push
