import asyncio
import logging
import sys
import traceback

from dataclasses import dataclass
from enum import Enum

import sissyBot.errors as errors
import sissyBot.proto.packet_pb2 as packet_pb2


LEN_HEADER = 1
LEN_ORDER = "big"


def get_pkt_len(buff):
    return int.from_bytes(buff[:LEN_HEADER], byteorder=LEN_ORDER, signed=False)


def get_1st_pkt(buff):
    len_ = get_pkt_len(buff)
    buff = buff[LEN_HEADER:]
    pkt = buff[:len_]
    remaining_buff = buff[len_:]
    return pkt, remaining_buff


def insert_pkt_len(buff):
    len_ = len(buff)
    len_bytes = len_.to_bytes(length=LEN_HEADER, byteorder=LEN_ORDER, signed=False)
    return len_bytes + buff


def contains_pkt(buff):
    if not len(buff):
        return False

    len_ = int.from_bytes(buff[:LEN_HEADER], byteorder="big", signed=False)

    if not len_:
        raise errors.BadStreamError()

    buff = buff[LEN_HEADER:]
    print(f"{len_}:{len(buff)}")

    if len(buff) >= len_:
        return True

    return False


class ClientNetCon:
    def __init__(self, log):
        self.loop = asyncio.get_event_loop()
        self.stop_event = asyncio.Event(loop=self.loop)
        self.log = log

        self.tasks = []

        self.reader = None
        self.writer = None

        self.packet_processor = None

    def tick(self):
        # After you call stop, every call to run_forever will run just the
        # pending callbacks/tasks. This is how we will interleave the asyncio
        # and kivy.
        self.loop.stop()
        # As this is stopped, only pending tasks will run once.
        # print("enter loop")
        self.loop.run_forever()
        # print("exit loop")

        done_tasks = [task for task in self.tasks if task.done()]
        self.tasks = [task for task in self.tasks if not task.done()]

        if done_tasks:
            print(done_tasks)
            for task in done_tasks:
                if task.exception():
                    self.log.error(str(task.get_stack()))
                    self.log.error(str(task.exception()))

    def connect(self, addr, port, success_cb, error_cb):
        print(port)

        async def connect_task():
            self.reader, self.writer = await asyncio.open_connection(
                host=addr, port=port
            )
            self.log.info("connected!")

            self.packet_processor = PacketProcessor(
                self.reader, self.writer, self.stop_event, self.log
            )

            self.tasks.append(self.packet_processor.start())

        con_task = self.loop.create_task(connect_task())

        def callback(task):
            if task.exception():
                error_cb()
                return
            success_cb()

        con_task.add_done_callback(callback)

        self.tasks.append(con_task)


class PacketProcessor:
    def __init__(self, reader, writer, stop_event, log):
        self.reader = reader
        self.writer = writer

        self.stop_event = stop_event
        self.recv_task = None

        self.log = log

        self.handlers = {}

    def start(self):
        self.recv_task = asyncio.create_task(self.recv_fn())
        return self.recv_task

    def stop(self):
        self.stop_event.set()

    async def recv_fn(self):
        self.accum_buff = b""

        stop_task = asyncio.create_task(self.stop_event.wait())

        while True:
            recv_task = asyncio.create_task(self.reader.read(4096))
            done, pending = await asyncio.wait(
                {stop_task, recv_task}, return_when=asyncio.FIRST_COMPLETED
            )

            if stop_task in done:
                return

            assert recv_task in done
            assert len(done) == 1

            buff = recv_task.result()
            print(buff)

            if not len(buff):
                log.info("connection close, shutting down PacketProcessor.")
                return

            self.accum_buff += buff

            while contains_pkts(self.accum_buff):
                self.accum_buff = self._process_pkt(self.accum_buff)

    def _process_pkt(self, buff):
        pkt_buff, remain_buff = get_1st_pkt(buff)

        pkt = packet_pb2.FromString(pkt_buff)

        frame_type = pkt.WhichOneof("frame")

        if frame_type in self.handlers:
            frame = getattr(pkt, frame_type)
            self.handlers[frame_type](frame)
            return remain_buff

        log.error(f"Unhandled frame type: {frame_type}")
        return remain_buff
