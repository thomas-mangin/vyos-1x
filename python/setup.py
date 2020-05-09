import os
from setuptools import setup

setup(
    name = "vyos",
    version = "1.2.0",
    author = "VyOS maintainers and contributors",
    author_email = "maintainers@vyos.net",
    description = ("VyOS configuration libraries."),
    license = "LGPLv2+",
    keywords = "vyos",
    url = "http://www.vyos.io",
    packages=["vyos","vyos.ifconfig"],
    long_description="VyOS configuration libraries",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Utilities",
        "License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)",
    ],
    entry_points={
        "console_scripts": [
            "unix_daemon = vyos.entry.unix_daemon:main",
            "validator = vyos.entry.validator:main",
            "file-exists = vyos.validators.file-exists:main",
            "fqdn = vyos.validators.fqdn:main",
            "mac-address = vyos.validators.mac-address:main",
            "numeric = vyos.validators.numeric:main",
            "timezone = vyos.validators.timezone:main",
            "vrf-name = vyos.validators.vrf-name:main",
        ],
    }
)

