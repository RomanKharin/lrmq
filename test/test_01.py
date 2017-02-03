import unittest

import sys
import lrmq

class TestStartHub(unittest.TestCase):

    def test_subprocess(self):
        import subprocess
        # should enough for most cases
        interp = sys.argv[0].split(" ")[0]
        subprocess.run([interp, "-m", "lrmq"])

    def test_module(self):
        lrmq.main({"_": None})

if __name__ == '__main__':
    unittest.main()
