# we need to use hard tabs instead of spaces in makefiles!
# https://stackoverflow.com/a/14109796


all:
	clear
	black -l 80 *.py ./py2048/*.py


push:
	git push -u origin main


build:
	python3 -m build --no-isolation


upload:
	twine upload dist/*


clean:
	rm -rf ./build/ ./dist/ ./py2048base.egg-info/ ./py2048/__pycache__/
	find . -type f -name *.pyc -delete
	find . -type d -name __pycache__ -delete


.PHONY: all push build upload clean
