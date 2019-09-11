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

# import sissyBot.net
import sissyBot.robot

# from sissyBot.proto.packet_pb2 import Packet

from . import float_joy


class RootWidget(kivy.uix.boxlayout.BoxLayout):
    def on_addr_update(self, config):
        addr_str = config.get("robot", "address") + ":" + config.get("robot", "port")

        self.ids.address_label.text = addr_str


class DriveBinding:
    def __init__(self, bot_con):
        self._bot_con = bot_con

    def on_engage(self, pad):
        print(f"engadge! {pad}")

    def on_move(self, pad, theta, rho):
        print(f"moving {theta}, {rho}")
        self._bot_con.drive.cmd(theta, rho)

    def on_release(self, pad):
        print("release")
        self._bot_con.drive.stop()


class ConnectButton(kivy.uix.togglebutton.ToggleButton):

    bot_con = kivy.properties.ObjectProperty()

    def on_bot_con(self, _, bot_con):
        bot_con.bind(up=self.on_up)

    def on_press(self):
        self.text = "Connecting"

    def on_up(self, _, up):
        print("on_up")
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

    bot_con = kivy.properties.ObjectProperty()

    def on_start(self):
        self.log = self.root.ids.log
        # self.log = LogBinding(self.root.ids.log)
        # self.bot_con = sissyBot.net.ClientNetCon(self.log)
        self.bot_con = sissyBot.robot.Robot()
        # self.bot_con.start()

        self.drive_binding = DriveBinding(self.bot_con)

    def on_stop(self):
        self.bot_con.close()

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


def client():
    return ClientApp().run()
