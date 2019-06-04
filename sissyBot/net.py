import asyncio
import multiprocessing

from enum import Enum


class CmdEvents(Enum):
    STOP = 1


class NetProc:
    def __init__(self):
        self.tasks = []
        self.proc = None

        self.egress_que = multiprocessing.Queue()
        self.ingress_que = multiprocessing.Queue()
        self.stop_event = multiprocessing.Event()

    def start(self):
        self.proc = multiprocessing.Process(target=self.main)
        self.proc.start()

    def stop(self):
        self.stop_event.set()

        self.proc.join(5.0)
        print("proc jpined")

    def main(self):
        asyncio.run(self.main_task())
        print("main done")

    async def main_task(self):
        self.tasks = []
        loop = asyncio.get_running_loop()

        cmd_task = asyncio.create_task(self.cmd_que_task())

        await loop.run_in_executor(None, self.stop_event.wait)

        self.ingress_que.put(CmdEvents.STOP)
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
            cmd = await loop.run_in_executor(None, self.ingress_que.get)
            if cmd is CmdEvents.STOP:
                break


class NetConProc:
    def __init__(self):
        self.net_proc = NetProc()

    def start(self):
        self.net_proc.start()

    def stop(self):
        self.net_proc.stop()

    def echo(self, dat):
        self.net_proc.ingress_que.put(dat)
        return self.net_proc.egress_que.get()
