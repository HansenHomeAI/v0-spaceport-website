import setuptools

with open("README.md") as fp:
    long_description = fp.read()

setuptools.setup(
    name="spaceport_cdk",
    version="0.1.0",
    description="Spaceport Website Infrastructure",
    author="Spaceport",
    package_dir={"": "spaceport_cdk"},
    packages=setuptools.find_packages(where="spaceport_cdk"),
    install_requires=[
        "aws-cdk-lib>=2.0.0",
        "constructs>=10.0.0",
    ],
    python_requires=">=3.6",
) 