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


async def write_pkt(pkt, writer):
    buff = pkt.SerializeToString()
    buff = insert_pkt_len(buff)
    writer.write(buff)
    await writer.drain()


def contains_pkt(buff):
    if not len(buff):
        return False

    len_ = int.from_bytes(buff[:LEN_HEADER], byteorder="big", signed=False)

    if not len_:
        raise errors.BadStreamError()

    buff = buff[LEN_HEADER:]
    # print(f"{len_}:{len(buff)}")

    if len(buff) >= len_:
        return True

    return False


class PacketProcessor:
    def __init__(self, reader, writer, stop_event, log):
        self.reader = reader
        self.writer = writer

        self.stop_event = stop_event
        self.recv_task = None

        self.log = log

        self.handlers = {}

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

            if not len(buff):
                self.log.info("connection close, shutting down PacketProcessor.")
                return

            self.accum_buff += buff

            while contains_pkt(self.accum_buff):
                self.accum_buff = self._process_pkt(self.accum_buff)

    def _process_pkt(self, buff):
        pkt_buff, remain_buff = get_1st_pkt(buff)

        pkt = packet_pb2.Packet.FromString(pkt_buff)

        frame_type = pkt.WhichOneof("frame")

        if frame_type in self.handlers:
            frame = getattr(pkt, frame_type)
            self.handlers[frame_type](frame, self.writer)
            return remain_buff

        self.log.error(f"Unhandled frame type: {frame_type}")
        return remain_buff
