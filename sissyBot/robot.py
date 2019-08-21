import asyncio
import logging
import multiprocessing
import sys
import traceback

# from nats.aio.client import Client as NATS
import nats.aio.client

import snoop

from dataclasses import dataclass


@dataclass
class PubCmd:
    subject: str
    payload: bytes


@dataclass
class SubCmd:
    subject: str


class NatsProc:
    def __init__(self):
        self.proc = None

        self.gui_end, self.proc_end = multiprocessing.Pipe()

    def connect(self, addr):
        self.proc = multiprocessing.Process(target=self.main, args=(addr,))
        self.proc.start()
        self.proc_end.close()

    def stop(self):
        # self.gui_end.send(StopCmd())
        self.gui_end.close()
        self.proc.join()

    def main(self, addr):
        # close the gui end here
        self.gui_end.close()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.main_task(loop, addr))
        loop.close()

    async def main_task(self, loop, addr):
        self.nats = nats.aio.client.Client()

        await self.nats.connect(addr, loop)

        while True:

            try:
                cmd = await loop.run_in_executor(None, self.proc_end.recv)
                print(f"cmd: {cmd}")
            except EOFError:
                # closing proc
                tasks = asyncio.Task.all_tasks(loop)

                for task in tasks:
                    task.cancel()

                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                return

            if isinstance(cmd, PubCmd):
                sub = cmd.subject
                payload = cmd.payload

                asyncio.Task(self.nats.publish(sub, payload))

            elif isinstance(cmd, SubCmd):
                recv_end, send_end = multiprocessing.Pipe(False)
                self.proc_end.send(recv_end)

                async def sub_callback(msg):
                    subject = msg.subject
                    reply = msg.reply
                    data = msg.data.decode()
                    print(
                        "Received a message on '{subject} {reply}': {data}".format(
                            subject=subject, reply=reply, data=data
                        )
                    )

                    send_end.send(msg)

                sid = await self.nats.subscribe(cmd.subject, cb=sub_callback)


@snoop(depth=2)
def main():
    bp = NatsProc()
    bp.connect("127.0.0.1:4222")
    bp2 = NatsProc()
    bp2.connect("127.0.0.1:4222")

    cmd = SubCmd("boo")
    bp2.gui_end.send(cmd)
    sub_pipe = bp2.gui_end.recv()

    cmd = PubCmd("boo", b"1234")
    bp.gui_end.send(cmd)

    print(sub_pipe.recv())
    import time

    time.sleep(30.0)
    bp.stop()
    bp2.stop()


if __name__ == "__main__":
    main()
