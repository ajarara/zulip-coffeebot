from setuptools import setup, find_packages

setup(
    name='zulip-coffeebot',
    version='0.2.7',
    description='Coffee for all',
    url='https://github.com/alphor/zulip-coffeebot',
    author='Ahmad Jarara',
    author_email='ajarara94@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Coffee-Drinkers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        ],
    keywords='zulip coffee',
    packages=['coffeebot'],
    include_package_data=True,
    package_data={'coffeebot': ['zuliprc.conf']},
    extras_require={
        'test': ['pytest'],
    },
    entry_points={
        'console_scripts': [
            'coffeebot=coffeebot.coffeebot:main',
            ],
        },
    requires=['zulip'])
