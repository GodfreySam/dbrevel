from setuptools import find_packages, setup

setup(
    name="dbrevel-backend",
    version="0.0.0",
    packages=find_packages(exclude=("tests",)),
    include_package_data=True,
    description="DbRevel backend package (editable install)",
)
