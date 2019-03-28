import setuptools
import setuptools.command.install
import setuptools.command.develop
from pathlib import Path

class PostInstallCommand(setuptools.command.install.install,
                         setuptools.command.develop.develop):
    """Post-installation for develop and installation mode."""
    def run(self):
        try:
            import spacy
            return spacy.cli.validate()
        except ModuleNotFoundError:
            return

with open(Path(__file__).resolve().parent.joinpath('README.md'), 'r') as fh:
    long_description = fh.read()

with open(Path(__file__).resolve().parent.joinpath('requirements.txt'), 'r') as fh:
    requirements = [r.split('#', 1)[0].strip() for r in fh.read().split('\n')]

with open(Path(__file__).resolve().parent.joinpath('VERSION'), 'r') as fh:
    version = fh.read()

setuptools.setup(
    name='textpipe',
    version=version,
    description='textpipe: clean and extract metadata from text',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/textpipe/textpipe',
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3.6',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    install_requires=requirements,
    cmdclass={
        'develop': PostInstallCommand,
        'install': PostInstallCommand,
    },
)
