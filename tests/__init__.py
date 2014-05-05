# -*- coding: utf-8 -*-
"""
Tests for salon_spa module.

This module groups a few sub-modules containing unittest2 test cases.

Tests can be explicitely added to the `fast_suite` or `checks` lists or not.
See the :ref:`test-framework` section in the :ref:`features` list.

To run tests:
$ ./openerp-server -c .openerp_serverrc_marcos -d db -u module --log-level=test --test-enable

"""

# import test_ir_sequence
import test_salon_spa
import test_schedule

# When updated
fast_suite = [
    test_salon_spa,
    test_schedule,
]

# When installed
checks = [
]
