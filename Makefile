#!/usr/bin/env make -f

# for the shebang line, see:
# https://stackoverflow.com/a/7123267
# we need to use hard tabs instead of spaces in makefiles!
# https://stackoverflow.com/a/14109796

.DELETE_ON_ERROR:
.PHONY: test version push upload format clean
PY = python3
VERSION := $(shell $(PY) -I check_version.py)


build:
	$(PY) -m build --no-isolation


test:
	pytest-3 -v py2048/test.py


# do not indent (with tabs) Makefile directives such as ifeq
# https://stackoverflow.com/a/21226973
push:
ifeq ($(VERSION),)
	$(error You haven't updated the version tuple!)
else
	$(info Pushing version $(VERSION))
	git push -u origin main
	# erase commit.txt
	echo -n '' >commit.txt
endif


upload:
ifeq ($(VERSION),)
	$(error You haven't updated the version tuple!)
else
	$(info Uploading version $(VERSION))
	twine upload dist/*
endif


format:
	black -l 80 *.py ./py2048/*.py


clean:
	rm -rf ./build/ ./dist/ ./py2048base.egg-info/
	find . -type f -name *.pyc -delete
	find . -type d -name __pycache__ -delete
