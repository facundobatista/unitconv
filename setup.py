#!/usr/bin/fades

# Copyright 2020 Facundo Batista
# For further info, check  https://github.com/facundobatista/unitconv

import setuptools  # fades

with open("README.rst", "rt", encoding='utf8') as fh:
    long_description = fh.read()

with open("requirements.txt", "rt", encoding='utf8') as fh:
    requirements = fh.read().split('\n')

setuptools.setup(
    name="unitconv",
    version="1",
    author="Facundo Batista",
    author_email="facundo@taniquetil.com.ar",
    description=(
        "A units converter that understands a lot of written queries and produce "
        "a nice human response"),
    long_description=long_description,
    long_description_content_type="text/rest",
    url="https://github.com/facundobatista/unitconv",
    packages=setuptools.find_packages(),
    package_data={'': ["LICENSE", "requirements.txt"]},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': ["unitconv = unitconv:main"],
    },
    python_requires='>=3',
    install_requires=requirements,
)
