import kivy as kv

import kivy.app
import kivy.uix
import kivy.uix.widget
import kivy.uix.boxlayout

from . import float_joy


class RootWidget(kivy.uix.boxlayout.BoxLayout):
    pass


class ClientApp(kv.app.App):
    def build(self):
        return RootWidget()


def client():
    return ClientApp().run()
