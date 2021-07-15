import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="tiffexplore",
    packages=["tiffexplore"],
    version="2021.07.1",
    author="Wim Pomp",
    author_email="wimpomp@gmail.com",
    description="Explore a tiff structure.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
    install_requires=['numpy', 'tifffile', 'PyQt5'],
    scripts=['bin/tiffexplore'],
)
