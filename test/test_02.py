import unittest

import os
import sys
import lrmq
from lrmq.logs import LogTypes
import timeout_decorator
import tempfile

import pickle
import struct

import asyncio

TEST_TIMEOUT = 5 # it can fail in slow environment

    
class TestRPC(unittest.TestCase):

    def read_log(self, fn):
        logs = []
        with open(fn, "rb") as f:
            while True:
                slen = f.read(4)
                if not slen:
                    break
                slen = struct.unpack(">L", slen)[0]
                data = pickle.loads(f.read(slen))
                logs.append(data)
        self.assertGreater(len(logs), 0)
        return logs
        
    def verify_log(self, fn, pattern):
        "Compare existing log with pattern"    
        skip = 0
        for log in self.read_log(fn):
            log_id = None
            if "log_id" in log:
                if log["log_id"] == LogTypes.MARK: continue
                if skip > 0:
                    skip -= 1
                    continue
                p = pattern.pop(0)
                if p[0] == "return": return
                if p[0] == "skip": return
                # check level
                if p[0]:
                    self.assertEqual(p[0], log["levelname"])
                # check log_id
                if p[1]:
                    self.assertEqual(p[1], log["log_id"])
                # check etc
                if p[2]:
                    args = p[2].get("args")
                    if args:
                        if callable(args):
                            args(log["args"])
                        else:
                            self.assertEqual(args, log["args"])
                    extra = p[2].get("extra")
                    if extra:
                        if callable(extra):
                            args(log["extra"])
                        else:
                            self.assertEqual(extra, log["extra"])

    def setUp(self):
        # reinitialize loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # prepare test folder
        self.logdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.logdir.cleanup()

    @timeout_decorator.timeout(TEST_TIMEOUT)
    def test_agent_not_found(self):
        logname = os.path.join(self.logdir.name, "not_found")
        code = lrmq.main({
            "debuglogger": logname + ".pkl",
            "loglevel": "DEBUG",
            "log": logname + "_hub.log",
            "agents": [{
                "type": "stdio",
                "name": "agent_dump",
                "cmd": "test/agent_not_found"
             }]})
        assert code == 0
        
        def check_msg_args(args, event):
            self.assertEqual(args[0], "system/" + event + "_agent/agent_dump")
            pass
        
        self.verify_log(logname + ".pkl", [
            ["DEBUG", LogTypes.HUB_LOAD_MODE, {"args": ('config',)}],
            ["DEBUG", LogTypes.HUB_AGENT_COUNT, {"args": (1,)}],
            ["DEBUG", LogTypes.HUB_LOAD_AGENT, {}],
            ["INFO", LogTypes.HUB_START, {}],
            ["DEBUG", LogTypes.HUB_MESSAGE, {"args": lambda x: 
                check_msg_args(x, "prepare")}],
            ["DEBUG", LogTypes.HUB_MESSAGE, {"args": lambda x: 
                check_msg_args(x, "error")}],
            ["INFO", LogTypes.HUB_LOOP_END, {}],
            ["INFO", LogTypes.HUB_FINISH, {}],
            ["return"]
        ])

    @unittest.skip("Unimplemented")
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
        for log in self.read_log(logname + ".pkl"):
            log_id = None
            if "log_id" in log:
                print(log)

if __name__ == '__main__':
    unittest.main()
