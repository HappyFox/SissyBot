import logging

import kivy as kv

import kivy.app
import kivy.clock
import kivy.properties
import kivy.uix
import kivy.uix.widget
import kivy.uix.boxlayout
import kivy.utils

import sissyBot.net

from . import float_joy


class RootWidget(kivy.uix.boxlayout.BoxLayout):
    def on_addr_update(self, config):
        addr_str = config.get("robot", "address") + ":" + config.get("robot", "port")

        self.ids.address_label.text = addr_str


class ClientApp(kv.app.App):
    use_kivy_settings = False

    def on_start(self):
        # ugh a bit of a circular design, have to come up with something
        # better.
        self.net_con = sissyBot.net.ClientNetCon(self)
        # self.net_con.start()

        self.clock = kivy.clock.Clock
        self.clock.schedule_interval(self.tick, 0)

    def on_stop(self):
        # self.net_con.stop()
        pass

    def tick(self, dt):
        self.net_con.tick()

    def connect(self, *largs):
        print(largs)
        print("toggle!")
        addr = self.config.get("robot", "address")
        port = self.config.get("robot", "port")

        self.root.ids.connect_btn.text = "Connecting"

        def on_connect():
            self.root.ids.connect_btn.text = "Connected"

        def on_error():
            self.root.ids.connect_btn.state = "normal"
            self.root.ids.connect_btn.text = "Connect"

        self.net_con.connect(addr, port, on_connect, on_error)

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

        self.root.ids.log.text += f"\n{text}\n"

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
