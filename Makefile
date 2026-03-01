deploy:
	pipreqs . --force
	git add .
	git commit -m "prepare for deploy"
	git push
