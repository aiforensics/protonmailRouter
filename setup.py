from setuptools import setup

CURRENT_PYTHON = sys.version_info[:2]
REQUIRED_PYTHON = (3, 8)

if CURRENT_PYTHON < REQUIRED_PYTHON:
    sys.stderr.write(
        """This program requires at least Python {}.{}, but you're trying to install it on Python {}.{}.
Please upgrade your python version""".format(
            *(REQUIRED_PYTHON + CURRENT_PYTHON)
        )
    )
    sys.exit(1)


requires = [
    'pexpect>4.8,<5',
    'ptyprocess>=0.7.0,<1',
    'PyYAML>=6.0',
]

test_requirements = []
setup(
    name='protonmailRouter',
    version='0.0.6',
    description='Mailing list hack for protonmail',
    author='Pandry',
    author_email='pandry@pm.me',
    url='https://github.com/aiforensics/protonmailRouter',
    python_requires=">=3.8",
)
