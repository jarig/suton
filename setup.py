import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="suton",
    version="0.0.1",
    author="Jaroslav Gor",
    author_email="gjarik@gmail.com",
    description="Set of libraries to provisioning and maintenance of TON Validator node",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jarig/suton",
    package_dir={'': 'src'},
    packages=['suton'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
         'paramiko==3.4.0',
    ],
    include_package_data=True,
    python_requires='>=3.6',
)
