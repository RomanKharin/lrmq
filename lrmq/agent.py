# -*- coding: utf8 -*-

# Low-resource message queue framework
# Standard agents
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
import logging
import asyncio
import re
import types

class Agent:
    "Base class for all agents"

    protocols = {}

    @classmethod
    def reg_protocol(cls, label, proto):
        cls.protocols[label] = proto

    def __init__(self, hub, name):
        self.hub = hub
        if name is None:
            name = hub.genid("agent")
        self.name = name
        # requester mode: 0 - normal, 1 - event subscription
        #self.isdone = asyncio.futures.Future()
        self.isloop = True
        # messages
        self.q = []
        self.q_s = None
        self.subs = []
        self.logger = logging.getLogger("log_" + name)
        self.ev_msg = {} # messages for events: prepare, new, lost, exit, error

    async def prepare(self):
        "Prepare loop"
        
        self.hub.logger.debug("Prepare agent " + self.name)
        self.send_agent_event("prepare")

    async def negotiate(self):
        "Negotiate protocol"
        
        pr = b"|".join(Agent.protocols.keys()) + b"\n"
        self.send(pr)
        await self.flush()
        # read confirmation
        sp = (await self.readline()).strip()
        if sp:
            self.logger.debug("Selected protocol for " + self.name + ": " + \
                sp.decode("utf-8"))
            self.select_protocol(Agent.protocols[sp])
        else:
            self.isloop = False
            self.logger.debug("Lost agent channel " + self.name)
            self.hub.logger.debug("Lost agent channel " + self.name)
            self.send_agent_event("lost")

    def select_protocol(self, mixin):
        "Use mixin methods for exchange"

        self.recv_request = types.MethodType(mixin.recv_request, self)
        self.send_answer = types.MethodType(mixin.send_answer, self)

    async def run(self):
        "Main loop"

        if not self.isloop: raise Exception("Can't rerun")
        try:
            await self.prepare()
        except Exception as e:
            self.logger.exception("while preparing")
            self.isloop = False
            self.send_agent_event("error")
            return

        # report event
        self.logger.debug("Run agent " + self.name)
        self.send_agent_event("new")

        try:
            await self.negotiate()
        except Exception as e:
            self.logger.exception("while negotiate")
            self.isloop = False
            self.send_agent_event("error")
            return

        cmd_recv = asyncio.Queue(1)
        async def receiver():
            while self.isloop:
                req = await self.recv_request()
                if req == "-": 
                    self.logger.debug("Signal for " + self.name)
                    self.signal()
                    continue
                self.logger.debug("Read " + str(req))
                await cmd_recv.put(req)
        recv_task = asyncio.ensure_future(receiver())
        while self.isloop:
            req = await cmd_recv.get()
            if not req:
                # stream lost
                self.logger.debug("Lost agent " + self.name)
                self.hub.logger.debug("Lost agent " + self.name)
                self.send_agent_event("lost")
                self.isloop = False
                break
            try:
                ans = await self.make_answer(req)
            except Exception as e:
                self.logger.exception("in agent loop")
                ans = {"answer": "error", "msg": repr(e)}
            cid = req.get("id")
            if cid is not None:
                ans["id"] = cid
            self.logger.debug("Write " + str(ans))
            await self.send_answer(ans)
        recv_task.cancel()
        self.logger.debug("Finish agent " + self.name)
        self.hub.logger.debug("Finish agent " + self.name)
        for subid in self.subs:
            self.logger.debug("Unsubscribe " + str(subid))
            self.hub.unsubscribe(subid)
        self.send_agent_event("exit")
        await self.finish()

    def send_agent_event(self, ev):
        aid = self.getid()
        self.hub.push_msg("system/" + ev + "_agent/" + self.name, 
            {"agentid": aid})
        if ev in self.ev_msg:
            self.hub.push_msg(self.ev_msg[ev], 
                {"agentid": aid, 
                "name": self.name,
                "event": ev})

    def signal(self, result = True):
        if self.q_s is not None:
            self.q_s.set_result(True)

    def push_msg(self, subid, name, msg):
        "Push message to queue"

        self.logger.debug("Message " + name + " " + str(msg))
        self.q.append((subid, name, msg))
        self.signal()

    def getid(self):
        "Return agentid"
        
        return None # None until not started

    async def make_answer(self, req):
        "Calculate answer"

        cmd = req.get("cmd")
        if hasattr(self, "cmd_" + cmd):
            return await getattr(self, "cmd_" + cmd)(req)
            return ans
        raise Exception("Unknown command '%s' from '%s'" % (cmd, self.getid()))

    async def cmd_ping(self, req):
        "Simple ping"

        return {"answer": "pong", "_req": req}

    async def cmd_getid(self, req):
        "Return agent ID"

        return {"answer": "ok", "agentid": self.getid()}

    async def cmd_exit(self, req):
        "End communications"

        self.isloop = False
        return {"answer": "ok", "msg": "bye!"}

    async def cmd_sub(self, req):
        "Subscribe to message(s)"

        try:
            mask = re.compile(req.get("mask"))
            subid = self.hub.subscribe(mask = mask, subscriber = self)
            self.subs.append(subid)
            self.logger.debug("Subscribe " + str(subid))
            return {"answer": "ok", "subid": subid}
        except Exception as e:
            return {"answer": "error", "msg": str(e)}

    async def cmd_wait_msg(self, req):
        "Get new messages. Wait if necessary"

        def getpart():
            part = self.q[:10]
            self.q = self.q[10:]
            return {"answer": "ok", "msg": part, "empty": len(self.q) == 0}
        if self.q:
            return getpart()
        try:
            if not self.q and req.get("block"):
                # wait for new messages
                self.q_s = self.hub.loop.create_future()
                await self.q_s
                self.q_s = None
            return getpart()
        except Exception as e:
            return {"answer": "error", "msg": str(e)}

    async def cmd_start_agent(self, req):
        cfg = req.get("cfg")
        a = agent_factory(self.hub, cfg)
        self.hub.pending_agents.append(a)
        self.hub.signal()
        return {"answer": "ok"}

    async def cmd_push(self, req):
        name = req.get("name")
        msg = req.get("msg")
        self.hub.push_msg(name, msg)
        return {"answer": "ok"}

class AgentSystem(Agent):
    "System namespace agent"

    def __init__(self, hub):
        super().__init__(hub = hub, name = "<system>")
        self.logger = self.hub.logger

    def getid(self):
        return "<system>"

    async def heartbeat(self):
        while True:
            await asyncio.sleep(5)
            self.hub.push_pulse()

    async def run(self):
        pulse = asyncio.Task(self.heartbeat())
        while self.isloop:
            self.q_s = self.hub.loop.create_future()
            await self.q_s
            self.q_s = None
        if pulse:
            pulse.cancel()

    def push_msg(self, subid, name, msg):
        "Push message to system agent"

        self.logger.debug("Unprocessed message to system " + \
            str(name) + " " + str(msg))

class Proto4ByteJson():
    "4 byte + json protocols"

    async def recv_request(self):
        "Receive and parse JSON data from stream"

        plen = await self.recv(4)
        if not plen:
            return None

        plen = struct.unpack("!I", plen)[0]
        data = (await self.recv(plen)).decode("utf-8")
        return json.loads(data)

    async def send_answer(self, ans):
        "Format JSON data and send to stream"

        data = json.dumps(ans, ensure_ascii = False)
        data = data.encode("utf-8")
        self.send(struct.pack("!I", len(data)))
        self.send(data)
        await self.flush()

Agent.reg_protocol(b"4bj", Proto4ByteJson)

class ProtoNumJson():
    "Numeric + json protocols"

    async def recv_request(self):
        "Receive and parse JSON data from stream"

        plen = await self.readline().decode("latin-1").strip()
        if not plen:
            return None

        plen = int(plen, 10)
        data = (await self.recv(plen)).decode("utf-8")
        return json.loads(data)

    async def send_answer(self, ans):
        "Format JSON data and send to stream"

        data = json.dumps(ans, ensure_ascii = False)
        data = data.encode("utf-8")
        self.send(str(len(data)).encode("latin-1") + b"\n")
        self.send(data)
        await self.flush()

Agent.reg_protocol(b"numj", ProtoNumJson)

class AgentStdIO(Agent):
    "Agent connect to scheduler via stdin and stdout with 4b-json protocol"
    def __init__(self, hub, cfg):
        self.cfg = cfg
        self.name = cfg.get("name")
        super().__init__(hub, self.name)
        self.aid = cfg.get("id", self.cfg.get("cmd", ""))
        self.ev_msg = {k: v for k, v in cfg.get("events", {}).items()}
        self.proc = None

    async def prepare(self):
        await super().prepare()
        loglevel = self.cfg.get("loglevel", "INFO")
        self.logger.setLevel(loglevel)
        cmd = [self.cfg.get("cmd")]
        args = self.cfg.get("args")
        if args:
            cmd += args
        self.hub.logger.info("Start agent " + str(cmd))
        self.proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout = asyncio.subprocess.PIPE,
            stdin = asyncio.subprocess.PIPE)
        logfn = self.cfg.get("log")
        if logfn:
            hdlr = logging.FileHandler(logfn)
        else:
            hdlr = logging.StreamHandler(sys.stdout)
        if hdlr:
            hdlr.setFormatter(self.hub.log_formatter)
            self.logger.addHandler(hdlr)
        self.logger.debug("=" * 25)
        self.logger.debug("Process created")

    async def recv(self, blen):
        return await self.proc.stdout.readexactly(blen)

    async def readline(self):
        return await self.proc.stdout.readline()

    def send(self, data):
        return self.proc.stdin.write(data)

    async def flush(self):
        return await self.proc.stdin.drain()

    async def finish(self):
        await self.proc.wait()

    def getid(self):
        if self.proc:
            if self.proc.pid is None:
                return "stdio-<lost>-%s" % (self.aid)
            else:
                return "stdio-%d-%s" % (self.proc.pid, self.aid)
        else:
            return None

    async def cmd_getid(self, req):
        ans = await super().cmd_getid(req)
        if req.get("cfg"):
            ans["cfg"] = self.cfg
        return ans

def agent_factory(hub, cfg):
    if not isinstance(cfg, dict):
        with open(cfg, "r") as f:
            cfg = json.load(f)
    atype = cfg.get("type")
    if atype == "stdio":
        return AgentStdIO(hub, cfg)
    else:
        raise Exception("Unknown agent type '%s'" % (atype))

