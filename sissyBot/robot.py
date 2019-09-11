import asyncio
import enum
import logging
import math
import multiprocessing
import sys
import traceback

# from nats.aio.client import Client as NATS
import nats.aio.client

# from nats.aio.errors import ErrConnectionClosed, ErrTimeout
import nats.aio.errors

import kivy.event

import snoop

from dataclasses import dataclass


from sissyBot.protobufs import drive_pb2


# @dataclass
class PubCmd:
    subject: str
    payload: bytes


@dataclass
class SubCmd:
    subject: str


class ConnState(enum.Enum):
    UP = 1
    DOWN = 2


class NatsProc:
    def __init__(self):
        self.proc = None

        self.gui_end, self.proc_end = multiprocessing.Pipe()

        self.sub_queues = []
        self.conn_state_recv_end, self.conn_state_send_end = multiprocessing.Pipe(False)

    def connect(self, addr):
        self.proc = multiprocessing.Process(target=self.main, args=(addr,))
        self.proc.start()
        self.proc_end.close()

    def close(self):
        # self.gui_end.send(closeCmd())
        self.gui_end.close()
        self.proc.join()

    async def _shutdown(self):
        for queue in self.sub_queues:
            queue.close()
        self.proc_end.close()

        loop = asyncio.get_event_loop()
        tasks = asyncio.Task.all_tasks(loop)

        for task in tasks:
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

        self.conn_state_send_end.send(ConnState.DOWN)

    def main(self, addr):
        # close the gui end here
        self.gui_end.close()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.main_task(loop, addr))
        loop.close()

    async def main_task(self, loop, addr):
        self.nats = nats.aio.client.Client()

        await self.nats.connect(addr, loop)
        self.conn_state_send_end.send(ConnState.UP)

        while True:

            try:
                cmd = await loop.run_in_executor(None, self.proc_end.recv)
                print(f"cmd: {cmd}")
            except EOFError:
                await self._shutdown()

                return

            if isinstance(cmd, PubCmd):
                sub = cmd.subject
                payload = cmd.payload

                try:
                    await self.nats.publish(sub, payload)
                except nats.io.errors.ErrConnectionClosed:
                    await self._shutdown()
                    return

            elif isinstance(cmd, SubCmd):
                recv_end, send_end = multiprocessing.Pipe(False)

                self.proc_end.send(recv_end)
                self.sub_queues.append(send_end)

                async def sub_callback(msg):
                    send_end.send(msg)

                # when I add unsub I will need this sid
                _ = await self.nats.subscribe(cmd.subject, cb=sub_callback)


class Robot(kivy.event.EventDispatcher):
    up = kivy.properties.BooleanProperty(False, force_dispatch=True)

    def __init__(self, **kwargs):
        super(Robot, self).__init__(**kwargs)
        self.nat_proc = None
        self.drive = Drive(self)

    def connect(self, addr, port):
        addr = f"{addr}:{port}"
        print(addr)
        self.nat_proc = NatsProc()
        self.nat_proc.connect(addr)

        self.clock = kivy.clock.Clock
        self.event = self.clock.schedule_interval(self.check_up, 0.2)

    def check_up(self, dt):
        msg = None
        while self.nat_proc.conn_state_recv_end.poll():
            print("got something")
            msg = self.nat_proc.conn_state_recv_end.recv()

        if msg:
            if msg == ConnState.UP and not self.up:
                print("we up !")
                self.up = True
            elif msg == ConnState.DOWN and self.up:
                print("we down !")
                self.up = False

    def close(self):
        if self.nat_proc:
            self.nat_proc.gui_end.close()

    def tick(self, dt):
        print("tick!")

    def publish(self, subject, payload):
        if not isinstance(payload, bytes):
            raise TypeError(f"Expected bytes got {type(payload)}")

        if not self.nat_proc:
            # TODO add logging
            return

        cmd = PubCmd()
        cmd.subject = subject
        cmd.payload = payload
        self.nat_proc.gui_end.send(cmd)

    def subscribe(self, subject):

        cmd = SubCmd(subject)
        self.nat_proc.gui_end.send(cmd)

        return self.nat_proc.gui_end.recv()


class Drive:
    def __init__(self, robot):
        self.robot = robot

    def cmd(self, heading, throttle):

        frame = drive_pb2.DriveFrame()
        frame.drive.heading = int(math.degrees(heading))
        frame.drive.throttle = throttle

        self.robot.publish("drive.cmd", frame.SerializeToString())

    def stop(self):
        frame = drive_pb2.DriveFrame()
        frame.stop.SetInParent()

        self.robot.publish("drive.cmd", frame.SerializeToString())


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
    bp.drive.cmd(180, 1.0)
    bp.drive.stop()

    if sub_pipe.poll(3):
        # print(sub_pipe.recv())

        msg = sub_pipe.recv()
        msg = drive_pb2.DriveFrame.FromString(msg.data)
        print(msg)
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
