from setuptools import setup, find_packages

setup(
    name='flask-tenants',
    version='0.4.7',
    author='Cory Cline, Gabe Rust',
    author_email='support@flasktenants.com',
    description='A Flask extension for multi-tenancy support',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/Flask-Tenants/flask-tenants',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Flask>=1.1.2',
        'SQLAlchemy>=1.3.23',
        'psycopg2-binary==2.9.9',
        'Flask-SQLAlchemy==3.1.1',
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Framework :: Flask',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    python_requires='>=3.6',
)
