# vim:ts=4:sw=4:et:
# Copyright 2015-present Facebook, Inc.
# Licensed under the Apache License, Version 2.0

# no unicode literals
from __future__ import absolute_import, division, print_function

import json
import multiprocessing.dummy
import os
import os.path
import time

import pywatchman
import WatchmanTestCase

try:
    import unittest2 as unittest
except ImportError:
    import unittest


ThreadPool = multiprocessing.dummy.Pool


@WatchmanTestCase.expand_matrix
class TestAbortCookies(WatchmanTestCase.WatchmanTestCase):
    # @nocommit this test belongs elsewhere
    def test_recrawl_unblocks_paused_clock_sync(self):
        root = self.mkdtemp()
        self.watchmanCommand("watch", root)
        self.pauseWatchers()

        clock_thread_client = self.getClient()
        recrawl_thread_client = self.getClient(no_cache=True)

        def clock_thread():
            clock_thread_client.query("clock", root, {"sync_timeout": 2000})

        def recrawl_thread():
            time.sleep(1)
            recrawl_thread_client.query("debug-recrawl", root)

        run_functions_in_threads_and_join([
            clock_thread,
            recrawl_thread,
        ])

        # @nocommit assert that clock didn't crash

    # @nocommit this doesn't really test debug-abort-cookies the same test works
    # without it (test_recrawl_unblocks_paused_clock_sync).
    def test_clock_sync_retries_after_abort(self):
        root = self.mkdtemp()
        self.watchmanCommand("watch", root)
        self.pauseWatchers()

        clock_thread_client = self.getClient()
        abort_cookies_thread_client = self.getClient(no_cache=True)

        def clock_thread():
            clock_thread_client.query("clock", root, {"sync_timeout": 3000})

        def abort_cookies_thread():
            time.sleep(1)
            abort_cookies_thread_client.query("debug-abort-cookies", root)
            time.sleep(1)
            abort_cookies_thread_client.query("debug-recrawl", root)

        run_functions_in_threads_and_join([
            clock_thread,
            abort_cookies_thread,
        ])

        # @nocommit assert that clock didn't crash

    # @nocommit deduplicate
    def pauseWatchers(self):
        self.watchmanCommand("debug-pause-watchers")
        # @nocommit we need to wait for ack from watchers...
        import time
        time.sleep(0.1)

    # @nocommit deduplicate
    # @nocommit this isn't necessary if we use one watchman server per test.
    def tearDown(self):
        self.watchmanCommand("debug-unpause-watchers")


def run_functions_in_threads_and_join(functions, timeout=None):
    try:
        pool = ThreadPool(processes=len(functions))
        # @nocommit timeout should be global, not local
        async_result = pool.map_async(lambda f: f(), functions)
        return async_result.get(timeout=timeout)
    finally:
        pool.close()
