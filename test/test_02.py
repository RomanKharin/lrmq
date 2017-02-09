import unittest

import os
import sys
import lrmq
import timeout_decorator
import tempfile

import pickle
import struct

import asyncio

TEST_TIMEOUT = 5 # it can fail in slow environment

def read_log(fn):
    logs = []
    with open(fn, "rb") as f:
        while True:
            slen = f.read(4)
            if not slen:
                break
            slen = struct.unpack(">L", slen)[0]
            data = pickle.loads(f.read(slen))
            logs.append(data)
    assert len(logs) > 0
    return logs
    
class TestRPC(unittest.TestCase):

    def setUp(self):
        # reinitialize loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # prepare test folder
        self.logdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.logdir.cleanup()

    @timeout_decorator.timeout(TEST_TIMEOUT)
    def test_single_master(self):
        logname = os.path.join(self.logdir.name, "single_master")
        code = lrmq.main({
            "debuglogger": logname + ".pkl",
            "loglevel": "DEBUG",
            "log": logname + "_hub.log",
            "agents": [{
                "type": "stdio",
                "cmd": "test/msc1.py",
                "id": "test02_master",
                "name": "test02_master",
                "log": logname + "_master.log",
                "loglevel": "DEBUG",
                "args": ["master"]}
            ]
        })
        assert code == 0
        for log in read_log(logname + ".pkl"):
            log_id = None
            if "log_id" in log:
                print(log)

if __name__ == '__main__':
    unittest.main()
