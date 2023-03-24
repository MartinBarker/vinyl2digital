import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="vinyl2digital",
    version="1.0.5",
    author="Martin Barker",
    author_email="martinbarker99@gmail.com",
    description="Batch render an audacity recording",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MartinBarker/vinyl2digital",
    packages=setuptools.find_packages(),
    install_requires=[
        'requests',
        'mutagen',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)