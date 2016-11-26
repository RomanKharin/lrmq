# -*- coding: utf8 -*-

# Low-resource message queue framework
# Access hub with tcp socket
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

import os
import sys
import asyncio
from asyncio.streams import StreamWriter, FlowControlMixin


async def run(port):
    loop = asyncio.get_event_loop()
    # out command queue
    ans_queue = asyncio.Queue()
    
    stdreader = None
    stdwriter = None
    
    # stdio initiation
    # NOTE: os.fdopen(0, "wb") will not works in pipe
    #       os.fdopen(sys.stdout, "wb") may crash print()
    writer_transport, writer_protocol = await loop.connect_write_pipe(
        FlowControlMixin, os.fdopen(sys.stdout.fileno(), "wb"))
    stdwriter = StreamWriter(writer_transport, writer_protocol, 
        None, loop)
    stdreader = asyncio.StreamReader()
    reader_protocol = asyncio.StreamReaderProtocol(stdreader)        
    await loop.connect_read_pipe(lambda: reader_protocol, sys.stdin.buffer)

    server_coro = None 

    async def onclient(reader, writer):
        # read from socket
        async def coro_reader():
            while True:
                data = await stdreader.readline()
                if not data: 
                    if server_coro:
                        server_coro.cancel()
                    break
                writer.write(data)
                await writer.drain()
        task = asyncio.ensure_future(coro_reader())
        while True:
            data = await reader.readline()
            if not data: 
                break
            stdwriter.write(data)
            await stdwriter.drain()
        task.cancel()
    
    server_coro = asyncio.start_server(onclient, port = port, backlog = 1)
    sock_server = await server_coro
    await sock_server.wait_closed()

def main():
    port = 5550
    if len(sys.argv) > 1:
        if sys.argv[1] in ("-h", "--help"):
            print("Start with:")
            print("\tpython3 -m lrmq -a python3 async_agent_socket.py 5550")
            print("Then connect with")
            print("\ttelnet 127.0.0.1 5550")
            return
        port = int(sys.argv[1])
    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
    else:
        loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run(port))
    finally:
        loop.close()    
    
if __name__ == "__main__":
    main()
