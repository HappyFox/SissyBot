import asyncio
import logging
import multiprocessing
import sys
import traceback

# from nats.aio.client import Client as NATS
import nats.aio.client

import snoop

from dataclasses import dataclass


from proto import drive_pb2


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

    def close(self):
        # self.gui_end.send(closeCmd())
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
                    send_end.send(msg)

                # when I add unsub I will need this sid
                _ = await self.nats.subscribe(cmd.subject, cb=sub_callback)


class Robot:
    def __init__(self):
        self.nat_proc = None

    def connect(self, addr):
        self.nat_proc = NatsProc()
        self.nat_proc.connect(addr)

    def close(self):
        self.nat_proc.gui_end.close()

    def publish(self, subject, payload):
        if not isinstance(payload, bytes):
            raise TypeError(f"Expected bytes got {type(payload)}")

        cmd = PubCmd(subject, payload)
        self.nat_proc.gui_end.send(cmd)

    def subscribe(self, subject):

        cmd = SubCmd(subject)
        self.nat_proc.gui_end.send(cmd)

        return self.nat_proc.gui_end.recv()

    def cmd_drive(self, heading, throttle):

        frame = drive_pb2.DriveFrame()
        frame.drive.heading = heading
        frame.drive.throttle = throttle

        # self.publish("drive.cmd", b"1234")
        # import pdb

        # pdb.set_trace()
        self.publish("drive.cmd", frame.SerializeToString())


@snoop(depth=2)
def main():
    bp = Robot()
    bp.connect("127.0.0.1:4222")
    bp2 = Robot()
    bp2.connect("127.0.0.1:4222")

    # cmd = SubCmd("boo")
    # bp2.gui_end.send(cmd)
    # sub_pipe = bp2.gui_end.recv()
    sub_pipe = bp2.subscribe("drive.cmd")

    # cmd = PubCmd("boo", b"1234")
    # bp.gui_end.send(cmd)
    # bp.publish("boo", b"1234")
    bp.cmd_drive(180, 1.0)

    if sub_pipe.poll(3):
        # print(sub_pipe.recv())

        msg = sub_pipe.recv()
        msg = drive_pb2.DriveFrame.FromString(msg.data)
        print(msg)

    import time

    # time.sleep(30.0)
    bp.close()
    bp2.close()


if __name__ == "__main__":
    main()
