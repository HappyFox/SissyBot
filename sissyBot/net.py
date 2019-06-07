import asyncio
import multiprocessing
import sys
import traceback

from dataclasses import dataclass
from enum import Enum


class CmdTypes(Enum):
    STOP = 1


@dataclass
class SetEndpoint:
    ip: str
    port: int


@dataclass
class ExceptionEvent:
    type_: type
    value: Exception
    frame_summary: traceback.StackSummary


class NetProc:
    def __init__(self):
        self.tasks = []
        self.proc = None

        self.resp_que = multiprocessing.Queue()
        self.cmd_que = multiprocessing.Queue()
        self.stop_event = multiprocessing.Event()

        self.cmd_handlers = {SetEndpoint: self.set_end_point}

    def start(self):
        self.proc = multiprocessing.Process(target=self.main)
        self.proc.start()

    def stop(self):
        self.stop_event.set()
        self.proc.join()

    def main(self):
        asyncio.run(self.main_task())

    async def main_task(self):
        self.tasks = []
        loop = asyncio.get_running_loop()

        cmd_task = asyncio.create_task(self.cmd_que_task())

        await loop.run_in_executor(None, self.stop_event.wait)

        self.cmd_que.put(CmdTypes.STOP)
        await cmd_task

        # stop is set, cancel tasks
        for task in self.tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass  # expected

    async def cmd_que_task(self):
        loop = asyncio.get_running_loop()

        while True:
            cmd = await loop.run_in_executor(None, self.cmd_que.get)
            if cmd is CmdTypes.STOP:
                break
            try:
                self.cmd_handlers[type(cmd)](cmd)
            except:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                stack = traceback.extract_tb(exc_traceback, capture_locals=False)
                excpt = ExceptionEvent(exc_type, exc_value, stack)
                self.resp_que.put(excpt)

    def set_end_point(self, cmd):
        print(f"{cmd.addr}:{cmd.port}")


class NetConProc:
    def __init__(self):
        self.net_proc = NetProc()
        self.cmd_que = self.net_proc.cmd_que
        self.resp_que = self.net_proc.resp_que

    def start(self):
        self.net_proc.start()

    def stop(self):
        self.net_proc.stop()
