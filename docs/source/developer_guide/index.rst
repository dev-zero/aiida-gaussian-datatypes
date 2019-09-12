===============
Developer guide
===============

Running the tests
+++++++++++++++++

The following will discover and run all unit test::

    pip install -e .[testing]
    pytest -v

Automatic coding style checks
+++++++++++++++++++++++++++++

Enable enable automatic checks of code sanity and coding style::

    pip install -e .[pre-commit]
    pre-commit install

After this, the `black <https://github.com/ambv/black>`_ formatter, 
the `flake8 <https://gitlab.com/pycqa/flake8>`_ linter
and the `flake8-bugbear <https://github.com/PyCQA/flake8-bugbear>`_ code analyzer will
run at every commit.

If you ever need to skip these pre-commit hooks, just use::

    git commit -n


Continuous integration
++++++++++++++++++++++

``aiida-gaussian-datatypes`` comes with a ``.travis.yml`` file for continuous integration tests on every commit using `Travis CI <http://travis-ci.com/>`_. It will:

#. run all tests for the ``django`` and ``sqlalchemy`` ORM
#. build the documentation
#. check coding style and version number (not required to pass by default)

Just enable Travis builds for the ``aiida-gaussian-datatypes`` repository in your Travis account. 

``aiida-gaussian-datatypes`` also includes an ``azure-pipelines.yml`` file for continuous integration tests using `Azure Pipelines <https://azure.microsoft.com/en-us/services/devops/pipelines/>`_.

Online documentation
++++++++++++++++++++

The documentation of ``aiida-gaussian-datatypes``
is ready for `ReadTheDocs <https://readthedocs.org/>`_:

Simply add the ``aiida-gaussian-datatypes`` repository on your RTD profile, preferably using ``aiida-gaussian-datatypes`` as the project name - that's it!


PyPI release
++++++++++++

Your plugin is ready to be uploaded to the `Python Package Index <https://pypi.org/>`_.
Just register for an account and::

    pip install twine
    python setup.py sdist bdist_wheel
    twine upload dist/*

After this, you (and everyone else) should be able to::

    pip install aiida-gaussian-datatypes

