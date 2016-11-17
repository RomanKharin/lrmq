# -*- coding: utf8 -*-

# Low-resource message queue framework
# Test hub: Master, Server, Client
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

from lrmq.client.sync import AgentIO

class AgentIOMaster(AgentIO):
    "Master agent"
    
    def init_loop(self):
        super().init_loop(True)
        print("MASTER", self.myid, file = sys.stderr)
        self.reg_callback(self.myid, self.msg_self)
        self.subscribe_check(self.myid + "/.*")
        def start_ext(mode):
            self.start_agent_check(cfg = {
                "type": self.cfg["type"],
                "id": self.cfg["id"].replace("master", mode),
                "name": self.cfg["name"].replace("master", mode),
                "log": self.cfg["log"].replace("master", mode), 
                "loglevel": self.cfg["loglevel"],
                "cmd": self.cfg["cmd"],
                "args": [self.cfg["args"][0], mode, self.myid],
                "events": {
                    "prepare": self.myid + "/prepare_" + mode,
                    "new": self.myid + "/new_" + mode,
                    "exit": self.myid + "/done_" + mode,
                    "error": self.myid + "/done_" + mode
                }
            })
        self.state = 0 # 0 - init, 1 - work
        self.serverid = None
        self.clientid = None
        start_ext("server")
        start_ext("client")
    
    def msg_self(self, ns, name, msg):
        print("to master", name, msg, file = sys.stderr)
        if name == "done_client":
            # shutdown server
            if self.serverid:
                self.push_msg_check(self.serverid + "/end", None)
                self.clientid = None
        if name == "done_server":
            self.serverid = None
            self.exit_check()
            self.end_loop()
            
        if self.state == 0:
            if name in ("server", "client"):
                if name == "server":
                    self.serverid = msg.get("serverid")
                else:
                    self.clientid = msg.get("clientid")
                if self.serverid and self.clientid:
                    # begin rpc communication
                    self.push_msg_check(self.clientid + "/start", 
                        {"rpc": self.serverid})
        else: # self.state == 1
            pass

class AgentIOServer(AgentIO):
    "Server agent"
    
    def init_loop(self):
        super().init_loop()
        print("SERVER", self.myid, file = sys.stderr)
        self.masterid = sys.argv[2]
        self.reg_callback(self.myid, self.msg_self)
        self.subscribe_check(self.myid + "/.*")
        self.reg_rpc("testfunc", self.rpc_testfunc)
        # notify master
        self.push_msg_check(self.masterid + "/server", 
            {"serverid": self.myid})
    
    def msg_self(self, ns, name, msg):
        print("to server", name, msg, file = sys.stderr)
        if name == "end":
            self.exit_check()
            self.end_loop()
            return
        return self.default_rpc(ns, name, msg)
        
        
    def rpc_testfunc(self, fn, args, reqid, sender):
        return ["Func=" + fn, "Args", args]
        
class AgentIOClient(AgentIO):
    "Client agent"
    
    def init_loop(self):
        super().init_loop()
        print("CLIENT", self.myid, file = sys.stderr)
        self.masterid = sys.argv[2]
        self.reg_callback(self.myid, self.msg_self)
        self.subscribe_check(self.myid + "/.*")
        # notify master
        self.push_msg_check(self.masterid + "/client", {"clientid": self.myid})
    
    def msg_self(self, ns, name, msg):
        print("to client", name, msg, file = sys.stderr)
        if name == "start":
            rpc = msg.get("rpc") # server rpc address
            print("RPC", rpc, file = sys.stderr)
            res = self.call_check(rpc, "testfunc", {"arg1": True, "arg2": 100})
            print("ANS", res, file = sys.stderr)
            self.exit_check()
            self.end_loop()

class AgentIOTest(AgentIO):
    def loop(self):
        self.send_req({"cmd": "ping", "_pid": os.getpid()})
        self.recv_ans()            
        self.send_req({"cmd": "getid"})
        ans = self.recv_ans()
        myid = ans.get("agentid")
        print("AGENT", myid, file = sys.stderr)
        self.send_req({"cmd": "sub", "mask": ".*"})
        ans = self.recv_ans()
        if ans.get("answer") != "ok":
            raise Exception("Protocol error: error at subscribe")
        subid = ans.get("subid")
        cnt = 3
        while True:
            self.send_req({"cmd": "wait_msg", "subid": subid, "block": True})
            ans = self.recv_ans()
            cnt -= 1
            if not cnt: break
        self.send_req({"cmd": "exit"})
        ans = self.recv_ans()
        if ans.get("answer") != "ok":
            raise Exception("Protocol error: error at exit")
    

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "master":
            a = AgentIOMaster()
        elif sys.argv[1] == "server":
            a = AgentIOServer()
        elif sys.argv[1] == "client":
            a = AgentIOClient()
        else:
            raise Exception("Unsupported mode " + sys.argv[1])
        a.start_loop()
    else:
        #print("Usage: testagent.py <mode>")
        import lrmq
        lrmq.main({
            "loglevel": "DEBUG",
            "agents": [
                {"name": "master",
                 "id": "test-master",
                 "type": "stdio",
                 "log": "",
                 "loglevel": "DEBUG",
                 "cmd": sys.executable,
                 "args": [sys.argv[0], "master"]
                
                }
            
            ]
        })
    
if __name__ == "__main__":
    main()

