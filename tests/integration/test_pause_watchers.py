# vim:ts=4:sw=4:et:
# Copyright 2015-present Facebook, Inc.
# Licensed under the Apache License, Version 2.0

# no unicode literals
from __future__ import absolute_import, division, print_function

import json
import os
import os.path

import pywatchman
import WatchmanTestCase


try:
    import unittest2 as unittest
except ImportError:
    import unittest


@WatchmanTestCase.expand_matrix
class TestPauseWatchers(WatchmanTestCase.WatchmanTestCase):
    # @nocommit these tests won't work concurrently. spawn one watchman server
    # per test.

    def test_pause_blocks_clock_sync(self):
        root = self.mkdtemp()
        self.watchmanCommand("watch", root)
        self.watchmanCommand("clock", root, {"sync_timeout": 1000})

        self.pauseWatchers()
        with self.assertRaisesRegexp(Exception, "timed out"):
            self.watchmanCommand("clock", root, {"sync_timeout": 100})

    def test_pause_blocks_initial_watch_clock_sync(self):
        root = self.mkdtemp()
        self.pauseWatchers()
        self.watchmanCommand("watch", root)
        with self.assertRaisesRegexp(Exception, "timed out"):
            self.watchmanCommand("clock", root, {"sync_timeout": 100})

    def test_pause_does_not_block_watch_and_query(self):
        root = self.mkdtemp()
        self.pauseWatchers()
        self.touchRelative(root, "new_file")
        self.watchmanCommand("watch", root)
        query_result = self.watchmanCommand("query", root, {
            "fields": ["name"],
            "sync_timeout": 0,
        })
        self.assertFileListsEqual(query_result["files"], ["new_file"])

    def test_pause_blocks_updated_query(self):
        root = self.mkdtemp()
        self.touchRelative(root, "old_file")
        self.watchmanCommand("watch", root)
        self.pauseWatchers()

        # @nocommit HACK prevent watch from seeing new_file
        import time
        time.sleep(0.5)
        self.touchRelative(root, "new_file")
        # @nocommit HACK if pause didn't work, wait for new_file to be noticed
        import time
        time.sleep(0.5)

        query_result = self.watchmanCommand("query", root, {
            "fields": ["name"],
            "sync_timeout": 0,
        })
        self.assertFileListsEqual(query_result["files"], ["old_file"])

    def test_pause_does_not_block_recrawl_and_query(self):
        root = self.mkdtemp()
        self.touchRelative(root, "old_file")
        self.watchmanCommand("watch", root)
        self.pauseWatchers()

        # @nocommit HACK prevent watch from seeing new_file
        import time
        time.sleep(0.5)
        self.touchRelative(root, "new_file")
        self.watchmanCommand("debug-recrawl", root)
        # @nocommit HACK wait for recrawl to see new_file
        import time
        time.sleep(0.5)

        query_result = self.watchmanCommand("query", root, {
            "fields": ["name"],
            "sync_timeout": 0,
        })
        self.assertFileListsEqual(query_result["files"], ["new_file", "old_file"])

    def test_pause_does_not_block_initial_subscription_event(self):
        self.skipUnlessPersistentSession()

        root = self.mkdtemp()
        self.touchRelative(root, "old_file")
        self.watchmanCommand("watch", root)
        self.watchmanCommand("clock", root, {"sync_timeout": 1000})

        self.pauseWatchers()
        self.watchmanCommand("subscribe", root, "file_subscription", {"fields": ["name"]})

        event = self.waitForSub("file_subscription", root=root, timeout=1, remove=False)
        self.assertIsNotNone(event)

    def test_pause_does_not_block_watch_and_initial_subscription_event(self):
        self.skipUnlessPersistentSession()
        root = self.mkdtemp()

        self.pauseWatchers()
        self.touchRelative(root, "old_file")
        self.watchmanCommand("watch", root)
        self.watchmanCommand("subscribe", root, "file_subscription", {"fields": ["name"]})

        event = self.waitForSub("file_subscription", root=root, timeout=1, remove=False)
        self.assertIsNotNone(event)

    def test_pause_blocks_subscription_events(self):
        self.skipUnlessPersistentSession()
        root = self.mkdtemp()
        self.watchmanCommand("watch", root)
        self.touchRelative(root, "old_file")
        self.watchmanCommand("subscribe", root, "new_file_subscription", {"fields": ["name"]})
        self.drainSubscriptionEvents(root, "new_file_subscription")

        self.pauseWatchers()
        self.touchRelative(root, "new_file")
        with self.assertRaisesRegexp(Exception, "timed out"): # @nocommit factor
            # @nocommit Why does waitForSub raise SocketTimeout? Shouldn't it
            # return None?
            _event = self.waitForSub("new_file_subscription", root=root, timeout=1, remove=False)
            self.assertIsNone(_event) # @nocommit improve diagnostics, but this might introduce a false positive

    def drainSubscriptionEvents(self, root, subscription_name):
        timeout_per_iteration = 0.3
        keep_draining = True
        while keep_draining:
            try:
                event = self.waitForSub(name=subscription_name, root=root, timeout=timeout_per_iteration, remove=True)
            except pywatchman.SocketTimeout:
                # @nocommit Why does waitForSub raise SocketTimeout? Shouldn't
                # it return None?
                event = None
            if event is None:
                keep_draining = False

    def pauseWatchers(self):
        self.watchmanCommand("debug-pause-watchers")
        # @nocommit we need to wait for ack from watchers...
        import time
        time.sleep(0.1)

    # @nocommit this isn't necessary if we use one watchman server per test.
    def tearDown(self):
        self.watchmanCommand("debug-unpause-watchers")
