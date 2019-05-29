import kivy as kv

import kivy.app
import kivy.uix
import kivy.uix.widget
import kivy.uix.boxlayout
import kivy.properties

from . import float_joy


class RootWidget(kivy.uix.boxlayout.BoxLayout):

    address_label = kivy.properties.ObjectProperty(None)

    def on_config_update(self, section, key, value):
        print(section)
        print(key)
        print(value)


class ClientApp(kv.app.App):
    use_kivy_settings = False

    def build(self):
        self.root = RootWidget()
        return self.root

    def build_settings(self, settings):
        # {"type": "title", "title": "Networking"},
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
        print(key + " " + value)


def client():
    return ClientApp().run()
