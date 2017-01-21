#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Compare list of tests produced by 'py.test --collect-only' with list of tests in Polarion
and output to csv file.
"""

# Licence: MPL 2.0
# Author: Martin Kourim <mkourim@redhat.com>

from __future__ import print_function, unicode_literals

import sys
import time
import ssl
import re
import argparse
import csv

from pylarion.work_item import TestCase
from suds import WebFault


# workaround for old cert shipped with Pylarion
# pylint: disable=protected-access
ssl._create_default_https_context = ssl._create_unverified_context


class PylarionCompareException(Exception):
    """Pylarion failed."""


def cmd_arguments():
    """Command line options."""

    parser = argparse.ArgumentParser(description='Polarion compare')
    parser.add_argument('-i', '--input',
                        metavar='FILE',
                        required=True,
                        help="File with pytest output, use '-' for stdin")
    parser.add_argument('-o', '--output',
                        metavar='FILE',
                        required=True,
                        help="csv file for output")
    parser.add_argument('-r', '--polarion-run',
                        action='store',
                        required=True,
                        help="Polarion Test Run name")
    parser.add_argument('-p', '--polarion-project',
                        action='store',
                        help="Polarion project name (default taken from pylarion config file)")
    return parser


def retry_query(fun, *args, **kwargs):
    """Re-try query when webservice call failed."""

    # Sometimes query fails with "WebFault: Server raised fault: 'Not authorized.'".
    # When re-tried, the same query often succeed.
    for retry in range(10):
        if retry != 0:
            time.sleep(0.5)  # sleep and try again
        try:
            return fun(*args, **kwargs)
        except WebFault as detail:
            pass

    # all retries failed, bailing out
    raise PylarionCompareException("Failed to query Polarion: {}".format(detail))


def parse_pytest(file_name):
    """Parse 'py.test --collect-only' output."""

    with open(file_name, 'r') if file_name != '-' else sys.stdin as infile:
        for line in infile:
            if '<Module ' in line:
                class_str = instance_str = function_str = ''
                module_str = re.search(r'\'(.*)\'', line).group(1) + '::'
            if '<Class ' in line:
                instance_str = function_str = ''
                class_str = re.search(r'\'(.*)\'', line).group(1) + '::'
            if '<Instance ' in line:
                function_str = ''
                instance_str = re.search(r'\'(.*)\'', line).group(1) + '::'
            if '<Function ' in line:
                function_str = re.search(r'\'(.*)\'', line).group(1)
                node_id = '{}{}{}{}'.format(module_str, class_str, instance_str, function_str)

                unique_id = (
                    node_id.replace('/', '.')
                    .replace('::()', '')
                    .replace('::', '.')
                    .replace('.py', ''))

                yield unique_id


class PylarionCompare(object):
    """Get Test Cases info from Polarion and compare it to py.test output."""

    def __init__(self, polarion_project, polarion_run):
        self.polarion_project = polarion_project
        self.polarion_run = polarion_run

    def compile_query(self, test_case_query):
        """Compile query for Test Case search."""

        test_records_str = 'TEST_RECORDS:("{}/{}")'.format(self.polarion_project, self.polarion_run)

        query = 'NOT status:inactive AND ' \
                'caseautomation.KEY:automated AND (({}) AND {})' \
                .format(test_records_str, test_case_query)
        return query

    def polarion_collect_testcases(self):
        """Collect Polarion Test Cases."""

        test_cases_list = retry_query(TestCase.query,
                                      query=self.compile_query('cfme.tests.*'),
                                      project_id=self.polarion_project,
                                      fields=['title', 'work_item_id', 'test_case_id', 'assignee'])
        cached_testcases = {}
        for test_case in test_cases_list:
            unique_id = test_case.test_case_id
            param_index = test_case.title.rfind('[')
            if param_index > 0:
                unique_id += test_case.title[param_index:]
            cached_testcases[unique_id] = test_case
        return cached_testcases

    def __call__(self, file_name):
        """Return list of tests that are missing in Polarion and list of tuples with test
        missing in source tree and it's Polarion assignee."""

        polarion_testcases = self.polarion_collect_testcases()

        in_polarion = set([uid for uid in polarion_testcases])
        in_tree = set(parse_pytest(file_name))

        not_in_pytest = []
        for uid in sorted(in_polarion - in_tree):
            try:
                assignee = polarion_testcases[uid].assignee[0].name
            except IndexError:
                assignee = None
            not_in_pytest.append((uid, assignee))

        return (sorted(in_tree - in_polarion), not_in_pytest)


def main():
    """Run this when launched from command line."""

    cmd_parser = cmd_arguments()
    args = cmd_parser.parse_args()

    if args.polarion_project:
        polarion_project = args.polarion_project
    else:
        polarion_project = 'RHCF3'
    if not polarion_project:
        print("Polarion project name is not set.", file=sys.stderr)
        sys.exit(1)

    compare = PylarionCompare(polarion_project, args.polarion_run)

    not_in_polarion, not_in_pytest = compare(args.input)

    with open(args.output, 'wb') as csvfile:
        cvswriter = csv.writer(csvfile, delimiter=str(';'),
                               quotechar=str('|'), quoting=csv.QUOTE_MINIMAL)

        cvswriter.writerow(['Tests not in Polarion'])
        for test in not_in_polarion:
            cvswriter.writerow([test])

        cvswriter.writerow([])
        cvswriter.writerow(['Tests not in pytest', 'Assignee'])
        for test, assignee in not_in_pytest:
            cvswriter.writerow([test, assignee if assignee else ''])


if __name__ == '__main__':
    main()
