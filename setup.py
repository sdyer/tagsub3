#!/usr/bin/env python

import setuptools

with open("README.md") as fh:
	long_description=fh.read()

setuptools.setup(
	name="tagsub3",
	version="1.68",
	author="Shawn Dyer",
	author_email="sdyer@dyermail.net",
	description="tagsub template formatting package",
	long_description=long_description,
	long_description_content_type="text/markdown",
	url="http://www.shawndyer.com/",
	packages=setuptools.find_packages(),
	classifiers=[
		"Programming Language :: Python :: 3",
		"License :: OSI Approved :: MIT License",
		"Operating System :: OS Independent",
	],
	python_requires=">=3.8",
)
