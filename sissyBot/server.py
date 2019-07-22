import asyncio
import functools
import logging
import signal

import sissyBot.net as net


async def client_handler(reader, writer, stop_event=None, tasks_list=None):
    log = logging.getLogger("client_handler")
    client = net.PacketProcessor(reader, writer, stop_event, log)

    def print_log(frame, writer):
        import pdb

        pdb.set_trace()
        print(f"ping:{frame.time}")
        log.info(f"ping{frame.time}")

    client.handlers["ping"] = print_log

    await client.recv_fn()


async def main(client_cb, port=4443):
    server = await asyncio.start_server(client_cb, port=port)

    addr = server.sockets[0].getsockname()
    print(f"Serving on {addr}")

    return server


def serve():
    FORMAT = "%(asctime)-15s %(message)s"
    logging.basicConfig(format=FORMAT)

    loop = asyncio.get_event_loop()

    stop_event = asyncio.Event()
    tasks = []

    client_cb = functools.partial(
        client_handler, stop_event=stop_event, tasks_list=tasks
    )

    svr_start_task = loop.create_task(main(client_cb))

    loop.run_until_complete(svr_start_task)

    server = svr_start_task.result()

    svr_task = loop.create_task(server.serve_forever())

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        stop_event.set()
        server.close()
        loop.run_until_complete(server.wait_closed())

        for task in tasks:
            loop.run_until_complete(task)
