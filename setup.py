from setuptools import setup

setup(
    name="pylarion-cfme-compare",
    version='0.0.1',
    url="NONE",
    description="compare test list in pytest with test list in Polarion",
    long_description=open('README.rst').read().strip(),
    author='Martin Kourim',
    author_email='mkourim@redhat.com',
    install_requires=['suds'],
    keywords='pylarion',
    scripts=['pylarion-cfme-compare.py'],
    classifiers=['Private :: Do Not Upload'],  # hack to avoid uploading to pypi
)
