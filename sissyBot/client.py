import logging
import math
import select
import socket

import kivy as kv

import kivy.app
import kivy.clock
import kivy.properties
import kivy.uix
import kivy.uix.widget
import kivy.uix.boxlayout
import kivy.uix.label
import kivy.uix.togglebutton
import kivy.utils

import sissyBot.net

from . import float_joy


class RootWidget(kivy.uix.boxlayout.BoxLayout):
    def on_addr_update(self, config):
        addr_str = config.get("robot", "address") + ":" + config.get("robot", "port")

        self.ids.address_label.text = addr_str


class DriveBinding:
    def __init__(self, net_con):
        self._net_con = net_con

    def on_engage(self, pad):
        print(f"engadge! {pad}")

    def on_move(self, pad, theta, rho):
        print(f"moving {theta}, {rho}")

    def on_release(self, pad):
        print("release")


class ConnectButton(kivy.uix.togglebutton.ToggleButton):

    net_con = kivy.properties.ObjectProperty()

    def on_net_con(self, _, net_con):
        net_con.bind(up=self.on_up)

    def on_press(self):
        self.text = "Connecting"

    def on_up(self, up2, up):
        print(up)
        print(up2)
        if up:
            self.text = "Connected"
            self.state = "down"
            return
        self.text = "Connect"
        self.state = "normal"


class LogPanel(kivy.uix.label.Label):
    def info(self, text):
        self._log_entry(logging.INFO, text)

    def error(self, text):
        self._log_entry(logging.ERROR, text)

    def debug(self, text):
        self._log_entry(logging.DEBUG, text)

    def _log_entry(self, level, text):
        text = kivy.utils.escape_markup(text)

        if level == logging.ERROR:
            text = f"[color=ff3333]{text}[/color]"

        self.text += f"\n{text}\n"


class ClientApp(kv.app.App):
    use_kivy_settings = False

    net_con = kivy.properties.ObjectProperty()

    def on_start(self):
        self.log = self.root.ids.log
        # self.log = LogBinding(self.root.ids.log)
        # self.net_con = sissyBot.net.ClientNetCon(self.log)
        self.net_con = NetConnection(self.log)  # , self.config)
        # self.net_con.start()

        self.drive_binding = DriveBinding(self.net_con)

        self.clock = kivy.clock.Clock
        self.clock.schedule_interval(self.tick, 0)

    def on_stop(self):
        # self.net_con.stop()
        pass

    def tick(self, dt):
        self.net_con.tick()

    def build(self):
        self.root = RootWidget()

        self.settings_fn = {
            "robot": {
                "address": self.root.on_addr_update,
                "port": self.root.on_addr_update,
            }
        }
        return self.root

    def build_settings(self, settings):
        json_data = """
        [



            {
                "type": "string",
                "title": "Address",
                "desc": "Destination address",
                "section": "robot",
                "key": "address"
            },
            {
                "type": "numeric",
                "title": "Port",
                "desc": "Destination port",
                "section": "robot",
                "key": "port"
            }
        ]
        """
        settings.add_json_panel("Networking", self.config, data=json_data)

    def build_config(self, config):
        config.setdefaults("robot", {"address": "sissybot.local", "port": "4443"})

    def on_config_change(self, config, section, key, value):
        print(section + " " + key + " " + value)

        if section in self.settings_fn:
            if key in self.settings_fn[section]:
                fn = self.settings_fn[section][key]
                fn(config)


class NetConnection(kivy.event.EventDispatcher):

    up = kivy.properties.BooleanProperty(False, force_dispatch=True)

    def __init__(self, log, **kwargs):
        self.log = log

        self._socket = None

        super(NetConnection, self).__init__(**kwargs)

    def tick(self):
        if self._socket:
            # print(type(self._socket))
            read, write, err = select.select(
                [self._socket], [self._socket], [self._socket], 0
            )

            if err:
                self.log.error("socket error!")
                self._close_sock()
                return

            if write:
                if not self.up:
                    self.log.info("setting net con to up")
                self.up = True

            if read:
                try:
                    buff = self._socket.recv(4096)
                except ConnectionError:
                    self._close_sock()

                else:
                    if not buff:
                        self._close_sock()
                        return

    def _close_sock(self):
        self.log.error("closing socket")
        self._socket.close()
        self._socket = None
        self.up = False

    def connect(self, addr, port):
        self.log.info(f"Connecting ! {addr}:{port}")
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setblocking(False)

        try:
            self._socket.connect((addr, int(port)))
        except BlockingIOError:
            pass


def client():
    return ClientApp().run()
