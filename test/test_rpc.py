# -*- coding: utf8 -*-

# Low-resource message queue framework
# Do RPC
# Copyright (c) 2016 Roman Kharin <romiq.kh@gmail.com>

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
import json

from lrmq.client.sync import AgentIO

class AgentIOCaller(AgentIO):
    "Caller agent"
    
    def init_loop(self):
        super().init_loop(True)
        print("CALLER", self.myid, file = sys.stderr)
        #self.reg_callback(self.myid, self.msg_self)
        self.subscribe_check(self.myid + "/.*")
        print("CALL", 
            self.call_aid, self.call_func, self.call_args, file = sys.stderr)
        ans = self.call(self.call_aid, self.call_func, self.call_args)
        print("RET", ans, file = sys.stderr)
        # leave hub
        self.exit_check()
        self.end_loop()

    def start_loop(self, aid, func, args):
        self.call_aid = aid
        self.call_func = func
        self.call_args = args
        super().start_loop()

def main():
    if len(sys.argv) < 3:
        print()
        print("Usage:")
        print("\tpython3 -m lrmq -a python test_rpc.py <aid> <func> <args>")
        print("Where:")
        print("\taid - agent id")
        print("\tfunc - function name")
        print("\targs - json formatted aguments ('[1, 2, 3]')")
    else:
        a = AgentIOCaller()
        args = json.loads(sys.argv[3])
        a.start_loop(sys.argv[1], sys.argv[2], args)

if __name__ == "__main__":
    main()
