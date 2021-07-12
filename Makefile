# we need to use hard tabs instead of spaces in makefiles!
# https://stackoverflow.com/a/14109796


.PHONY: test push upload format clean


build:
	python3 -m build --no-isolation


test:
	python3 -m py2048.tests


push:
	git push -u origin main


upload:
	twine upload dist/*


format:
	clear
	black -l 80 *.py ./py2048/*.py


clean:
	rm -rf ./build/ ./dist/ ./py2048base.egg-info/ ./py2048/__pycache__/
	find . -type f -name *.pyc -delete
	find . -type d -name __pycache__ -delete

