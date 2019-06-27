import asyncio
import logging
import sys
import traceback

from dataclasses import dataclass
from enum import Enum


class NetCon:
    def __init__(self, log):
        self.loop = asyncio.get_event_loop()
        self.log = log

        self.tasks = []

        self.reader = None
        self.writer = None

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
            print("connected!")

        con_task = self.loop.create_task(connect_task())

        def callback(task):
            if task.exception():
                error_cb()
                return
            success_cb()

        con_task.add_done_callback(callback)

        self.tasks.append(con_task)

    async def _recv_task(self):
        pass
