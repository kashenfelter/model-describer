from setuptools import setup

setup(
    name='whitebox',
    version='0.0.7.4',
    packages=['whitebox'],
    url='https://github.com/Data4Gov/WhiteBox_Production',
    license='MIT',
    author='Jason Lewris, Daniel Byler, Venkat Gangavarapu, Shruti Panda',
    author_email='jlewris@deloitte.com',
    description='Unlock model details and shine light on how your data is performing within regions of the model',
    download_url='https://github.com/data4gov/WhiteBox_Production/archive/v0.0.6.tar.gz',
    keywords=['whitebox', 'machine learning', 'data science'],
    package_data={'whitebox': ['*.txt']},
)
