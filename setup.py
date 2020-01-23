import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="audacityDiscogsExporter",
    version="0.1.0",
    author="Martin Barker",
    author_email="martinbarker99@gmail.com",
    description="A small example package",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MartinBarker/audacityDiscogsExporter",
    packages=setuptools.find_packages(),
    install_requires=[
        'requests',
        'json',
        'mutagen',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)