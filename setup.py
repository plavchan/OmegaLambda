import setuptools
import os

# Get requirements
thelibFolder = os.path.dirname(os.path.realpath(__file__))
requirementPath = thelibFolder + '/requirements.txt'
install_requires = []
if os.path.isfile(requirementPath):
    with open(requirementPath) as f:
        install_requires = f.read().splitlines()

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="omegalambda",
    version="1.2.3",
    author=["Michael Reefe", "Owen Alfaro", "Shawn Foster", "Vedhas Banaji"],
    author_email=["michael.reefe8@gmail.com", "owenalfaro@gmail.com", "sfoster@mail.rit.edu", ""],
    description="Automation of the GMU campus observatory telescope",
    long_description=long_description,
    long_description_content_type="text/x-md",
    packages=setuptools.find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    url="https://github.com/Kakon24/omegalambda",
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "Operating System :: Windows"
    ],
    python_requires='>=3.8'
)
