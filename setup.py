from setuptools import setup, find_packages

setup(
    name="mirage-honeypot",
    version="0.1.0",
    description="A lightweight Python honeypot for observing attacker behaviours",
    author="Jahanzaib Ashraf Mir",
    packages=find_packages(),
    py_modules=["run"],
    entry_points={"console_scripts": ["mirage=run:main"]},
)
