import asyncio
import functools
import signal

import sissyBot.net as net


async def client_handler(reader, writer, stop_event=None, tasks_list=None):
    print("got client")

    accum_buff = b""

    stop_task = asyncio.create_task(stop_event.wait())

    while True:
        recv_task = asyncio.create_task(reader.read(4096))
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
            print("connection close, shutting down PacketProcessor.")
            return

        accum_buff += buff
        print(f"accum buff {accum_buff}")

        while net.contains_pkt(accum_buff):
            # accum_buff, pkt = _process_pkt(accum_buff)
            pkt_buff, accum_buff = net.get_1st_pkt(accum_buff)

            print(pkt_buff)


def process_pkt(pkt, writer, stop_event):
    pass


async def main(client_cb, port=4443):
    server = await asyncio.start_server(client_cb, port=port)

    addr = server.sockets[0].getsockname()
    print(f"Serving on {addr}")

    return server


async def run_server(server):
    async with server:
        await server.serve_forever()


def serve():
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
