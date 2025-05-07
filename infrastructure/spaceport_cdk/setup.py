import setuptools

with open("README.md") as fp:
    long_description = fp.read()

setuptools.setup(
    name="spaceport_cdk",
    version="0.0.1",
    description="Spaceport CDK Infrastructure",
    author="Gabriel Hansen",
    package_dir={"": "spaceport_cdk"},
    packages=setuptools.find_packages(where="spaceport_cdk"),
    install_requires=[
        "aws-cdk-lib==2.89.0",
        "constructs>=10.0.0",
        "boto3>=1.20.0",
    ],
    python_requires=">=3.9",
) 