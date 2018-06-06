================
Moved to https://gitlab.com/mkourim/pylarion-cfme-compare
================
Compare list of tests produced by 'py.test --collect-only' with list of tests in Polarion
and output to csv file.

It is tailored to work with test case ids used by CFME QE team.

Requires 'pylarion' library that is not public at the moment.


Example commands
----------------
::

    $ py.test --runxfail --long-running --use-provider complete --collect-only > /tmp/cfme_tests_list.txt
    $ pylarion-cfme-compare.py -i /tmp/cfme_tests_list.txt -o /tmp/cfme_tests_comp.csv -r 5_7_1_00

See complete help::

    $ pylarion-cfme-compare.py --help


Install
-------
Install pylarion first::

    $ cd pylarion_repo
    $ pip install .

Create and edit pylarion config file ~/.pylarion according to Pylarion install instructions.

Install this plugin::

    $ cd pylarion-cfme-compare
    $ pip install .
