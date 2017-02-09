import unittest

import sys
import lrmq
import asyncio

class TestStartHub(unittest.TestCase):

    def setUp(self):
        # reinitialize loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    def test_subprocess(self):
        import subprocess
        # should enough for most cases
        interp = sys.argv[0].split(" ")[0]
        subprocess.check_call([interp, "-m", "lrmq"])

    def test_module(self):
        lrmq.main({"_": None})

if __name__ == '__main__':
    unittest.main()
