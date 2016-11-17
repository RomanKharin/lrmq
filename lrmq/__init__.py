# -*- coding: utf8 -*-

# Low-resource message queue framework
# Package file
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

__version__ = "0.0.1"
version_info = (0, 0, 1)

assert sys.version_info >= (3, 5, 2), \
    "Python 3.5.2. required for loop.create_future()"

from .hub import Hub
from .agent import (Agent, AgentJsonStream, AgentStdIO, 
    AgentSystem, agent_factory)

def main(cfg = None):
    import asyncio
    
    if not cfg:
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("-c", "--config", 
            help = "Configuration file (json)")
        parser.add_argument("-ll", "--loglevel", 
            help = "Override log level")
        parser.add_argument("-l", "--log", 
            help = "Log filename (default stdout)")
        args = parser.parse_args()

        if args.config:
            with open(args.config, "r") as f:
                cfg = json.load(f)
        else:
            cfg = {}
        if args.loglevel:
            try:
                cfg["loglevel"] = int(args.loglevel, 10)
            except ValueError:
                cfg["loglevel"] = args.loglevel
        if args.log:
            cfg["log"] = args.log

    hub = Hub()
    hub.load_config(cfg)

    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
    else:
        loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(hub.main_loop())
    finally:
        loop.close()


