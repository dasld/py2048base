# we need to use hard tabs instead of spaces in makefiles!
# https://stackoverflow.com/a/14109796

.DELETE_ON_ERROR:
.PHONY: test version push upload format clean
PY = python3
VERSION = $(shell $(PY) -I check_version.py)


build:
	$(PY) -m build --no-isolation


test:
	pytest-3 py2048/test.py


version:
	$(PY) -I check_version.py


# do not indent (with tabs) Makefile directives such as ifeq
# https://stackoverflow.com/a/21226973
push:
	$(info Pushing version $(VERSION))
ifneq ($(VERSION),OK)
	$(error You haven't updated the version tuple!)
else
	git push -u origin main
endif


upload:
	$(info Uploading version $(VERSION))
ifneq ($(VERSION),OK)
	$(error You haven't updated the version tuple!)
else
	twine upload dist/*
endif


format:
	black -l 80 *.py ./py2048/*.py


clean:
	rm -rf ./build/ ./dist/ ./py2048base.egg-info/
	find . -type f -name *.pyc -delete
	find . -type d -name __pycache__ -delete
