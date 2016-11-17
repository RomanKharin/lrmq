# -*- coding: utf8 -*-

# Low-resource message queue framework
# Synchronous message client
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
import struct

def check_answer(fn, name = None):
    def wrapped(*args, **kwargs):
        ans = fn(*args, **kwargs)
        assert ans.get("answer") == "ok", \
            "Error during " + (name if name else fn.__name__) + \
            " " + ans.get("msg", "")
        return ans
    return wrapped

class AgentIO:

    def __init__(self):
        self.cmdid = 0
        self.waitid = None
        self.myid = None
        self.isloop = False
        self.msgs = [] # all received messages
        self.msg_listeners = {} # named listeners
        self.msg_def_listener = None # default listener
        self.reqid = 0
        self.wait_req = {} # awaited requests
        self.wait_ans = {} # awaited requests
        self.rpc_listeners = {} # function listeners
        self.rpc_def_listener = None # default function listeners
    
    def send_req(self, req):
        "Send request"
        
        self.waitid = self.cmdid
        self.cmdid += 1
        req["id"] = self.waitid
        data = json.dumps(req, ensure_ascii = False)
        data = data.encode("utf-8")
        sys.stdout.buffer.write(struct.pack("!I", len(data)))
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()
    
    def recv_ans(self):
        "Receive answer"
    
        plen = sys.stdin.buffer.read(4)
        plen = struct.unpack("!I", plen)[0]
        data = sys.stdin.buffer.read(plen).decode("utf-8")
        ans =  json.loads(data)
        #print("ANS", ans, file = sys.stderr)
        cid = ans.get("id")
        if cid is None:
            raise Exception("Protocol error: cmdid not found, expected %d" %\
                (self.waitid))
        if cid != self.waitid:
            raise Exception("Protocol error: cmdid mismatch %d != %d" %\
                (self.waitid, cid))
        return ans

    def getid(self, cfg = False):
        "Get agent ID and configuration"
    
        self.send_req({"cmd": "getid", "cfg": cfg})
        return self.recv_ans()

    getid_check = check_answer(getid, "getting ID")

    def push_msg(self, name, msg):
        "Push message to hib"
    
        self.send_req({"cmd": "push", "name": name, "msg": msg})
        return self.recv_ans()

    push_msg_check = check_answer(push_msg, "push message")

    def subscribe(self, mask):
        "Subscribe to message(s)"
    
        self.send_req({"cmd": "sub", "mask": mask})
        return self.recv_ans()

    subscribe_check = check_answer(subscribe, "subscribe to messages")

    def wait_msg(self, block = True):
        "Wait for new message(s)"
    
        self.send_req({"cmd": "wait_msg", "block": block})
        return self.recv_ans()

    wait_msg_check = check_answer(wait_msg, "getting/waiting messages")

    def start_agent(self, cfg):
        "Start remote agent"
    
        self.send_req({"cmd": "start_agent", "cfg": cfg})
        return self.recv_ans()

    start_agent_check = check_answer(start_agent, "start agent")
    
    def exit(self):
        "Send normal exit message"
    
        self.send_req({"cmd": "exit"})
        return self.recv_ans()

    exit_check = check_answer(exit, "exit")

    def reg_callback(self, name, cb):
        "Register message callbacks"

        if name:
            self.msg_listeners[name] = cb
        else:
            self.msg_def_listener = cb

    def reg_rpc(self, fn, cb):
        "Register RPC callbacks"

        if fn:
            self.rpc_listeners[fn] = cb
        else:
            self.rpc_def_listener = cb
            
    def init_loop(self, cfg = False):
        "Loop initialization"
    
        self.reg_callback(None, self.default_message)
        ans = self.getid_check(cfg = cfg)
        self.myid = ans.get("agentid")
        self.cfg = ans.get("cfg")

    def process_msgs(self):
        "Process messages until exhaustion"
        
        if not self.msgs:
            ans = self.wait_msg_check(block = True)
            self.msgs += ans.get("msg", [])
        while self.msgs:
            subid, nsname, msg = self.msgs.pop(0)
            self.process_msg(nsname, msg)

    def process_msg(self, name, msg):
        "Process one message"
    
        # get namespace
        ns, name = name.split("/", 1)
        if ns == self.myid and name == "ret":
            # rpc for answers
            reqid = msg.get("reqid")
            if reqid in self.wait_req:
                self.wait_ans[reqid] = msg
                return
        if ns in self.msg_listeners:
            return self.msg_listeners[ns](ns, name, msg)
        if self.msg_def_listener:
            return self.msg_def_listener(ns, name, msg)

    def start_loop(self):
        "Main processing loop"
    
        self.isloop = True
        self.init_loop()
        while self.isloop:
            self.process_msgs()

    def end_loop(self):
        self.isloop = False

    def call(self, rpc, fn, args = None):
        "RPC from client"
        
        assert rpc, "RPC address can't be empty"
        reqid = self.reqid
        self.reqid += 1
        self.push_msg_check(rpc + "/call", {"fn": fn, "args": args, 
            "reqid": reqid, "from": self.myid})
        self.wait_req[reqid] = (reqid, rpc, fn, args)
        while reqid not in self.wait_ans:
            self.process_msgs()
        self.wait_req.pop(reqid)
        return self.wait_ans.pop(reqid)
        
    call_check = check_answer(call, "call rpc")

    def default_message(self, ns, name, msg):
        "Default message handler"

        if ns == "system" and name == "pulse": return
        if ns == self.myid and name == "call": 
            return self.default_rpc(ns, name, msg)
        print("Unprocessed", ns, name, msg, file = sys.stderr)

    def default_rpc(self, ns, name, msg):
        "Default RPC server handler"
    
        # process rpc
        if name != "call": return

        fn = msg.get("fn")
        args = msg.get("args")
        reqid = msg.get("reqid")
        sender = msg.get("from")
        
        try:
            if fn in self.rpc_listeners:
                ret = self.rpc_listeners[fn](fn, args, reqid, sender)
                msg = {"answer": "ok", "ret": ret}
            elif self.rpc_def_listener:
                ret = self.rpc_def_listener(fn, args, reqid, sender)
                msg = {"answer": "ok", "ret": ret}
            else:
                msg = {"answer": "error", "msg": "No function \"%s\"" % fn}
        except Exception as e:
            traceback.print_exc(file = sys.stderr)
            msg = {"answer": "error", "msg": repr(e)}
        msg["reqid"] = reqid
        self.push_msg_check(sender + "/ret", msg)


