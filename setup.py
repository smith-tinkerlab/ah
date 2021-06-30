from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='mirah',  
    version='0.0.0-alpha',
    description='mirah: Python package for building Aligned Hierarchies for music-based data streams.',  # Optional
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/smith-tinkerlab/aht',
    author='Katherine M. Kinnaird, Smith Tinkerlab',
    author_email='kkinnaird@smith.edu',
    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    python_requires='>=3.6, <4',
    install_requires=[
        'numpy >= 1.15.0',
        'scipy.io', 
        'pandas',
        'matplotlib'
    ],
    extras_require={
        'dev': ['check-manifest'],
        'test': ['coverage'],
    },
    project_urls={ 
        'Bug Reports': 'https://github.com/smith-tinkerlab/ah/issues',
        'Source': 'https://github.com/smith-tinkerlab/ah',
    },
    package_data={'mirah': ['input.csv']},
    include_package_data=True,
    license_file = ('LICENSE.md'),
    license='MIT',
    license_file_content_type = 'text/markdown',

)