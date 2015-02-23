from setuptools import setup

setup(
    name='qsnake',
    version='0.1',
    long_description=__doc__,
    packages=['qsnake'],
    include_package_data=True,
    install_requires=['Flask', 'Eve', 'qproject'],
)
