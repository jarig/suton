import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="suton", # Replace with your own username
    version="0.0.1",
    author="Jaroslav Gor",
    author_email="author@example.com",
    description="Set of libraries to provisioning and maintenance of TON Validator node",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jarig/suton",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_data={
        'docker': ['*']
    },
    python_requires='>=3.6',
)
