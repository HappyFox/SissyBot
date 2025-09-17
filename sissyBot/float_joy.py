"""
A widget that implements a floating joystick.
"""

import math

import kivy as kv
import kivy.app
import kivy.properties
import kivy.uix
import kivy.uix.widget


class Point:
    def __init__(self, *args):
        self.x = None
        self.y = None

        self.x, self.y = self._args_to_xy(args)

    def __getitem__(self, idx):
        if idx == 0:
            return self.x
        elif idx == 1:
            return self.y
        raise IndexError()

    def _args_to_xy(self, args):
        x = None
        y = None
        if len(args) == 1:
            arg = args[0]

            if hasattr(arg, "x") and hasattr(arg, "y"):
                return arg.x, arg.y

            x = arg[0]
            y = arg[1]
            return x, y

        elif len(args) == 2:
            x = args[0]
            y = args[1]
            return x, y

        raise TypeError("Invalid type pass")

    def _rel_coord(self, args):
        dx, dy = self._args_to_xy(args)

        x_dist = dx - self.x
        y_dist = dy - self.y

        return x_dist, y_dist

    def distance_to(self, *args):
        dx, dy = self._rel_coord(args)

        return math.hypot(dx, dy)

    def radians_to(self, *args):
        dx, dy = self._rel_coord(args)

        return math.atan2(dy, dx)

    def degrees_to(self, *args):
        return math.degrees(self.radians_to(*args))

    def polar_from(self, rads, len_):
        x = math.cos(rads) * len_
        y = math.sin(rads) * len_

        return x + self.x, y + self.y

    # return x, y


class JoyPad(kv.uix.widget.Widget):

    pad_color = kv.properties.ListProperty([0.5, 0.5, 0.5, 0.5])
    dish_color = kv.properties.ListProperty([0.3, 0.3, 0.3])
    pad_outline = kv.properties.ListProperty([0.2, 0.2, 0.2])

    knob_color = kv.properties.ListProperty([0.5, 0, 0, 0])
    knob_outline = kv.properties.ListProperty([0, 0, 0])

    shaft_color = kv.properties.ListProperty([0.1, 0.1, 0.1])

    pad_size = kv.properties.NumericProperty(0.5)
    dish_size = kv.properties.NumericProperty(0.6)
    knob_size = kv.properties.NumericProperty(0.5)
    shaft_size = kv.properties.NumericProperty(0.5)

    trim = kv.properties.NumericProperty(0.0)

    def __init__(self, **kwargs):
        self._td_pt = None
        self._td_pad = kv.graphics.InstructionGroup()
        self._dir_indicator = kv.graphics.InstructionGroup()
        self._active_touch = None

        self.register_event_type("on_engage")
        self.register_event_type("on_move")
        self.register_event_type("on_release")

        super(JoyPad, self).__init__(**kwargs)

        self.canvas.add(self._td_pad)
        self.canvas.add(self._dir_indicator)

    def on_engage(self):
        pass

    def on_move(self, theta, rho):
        pass

    def on_release(self):
        pass

    def _cal_sizes(self):
        min_size = min(self.width, self.height)
        self.pad_radius = (min_size * self.pad_size) / 2
        self.knob_radius = self.pad_radius * self.knob_size

        self.shaft_width = self.knob_radius * self.shaft_size

    def _draw_circle(self, x, y, radius):
        diam = radius * 2
        return kv.graphics.Ellipse(pos=(x - radius, y - radius), size=[diam, diam])

    def _draw_pad(self, x, y):
        self._td_pad.clear()
        self._td_pad.add(kv.graphics.Color(rgb=self.pad_color))
        self._td_pad.add(self._draw_circle(x, y, self.pad_radius))
        self._td_pad.add(kv.graphics.Color(rgb=self.pad_outline))
        self._td_pad.add(kv.graphics.Line(circle=(x, y, self.pad_radius)))

        dish_radius = self.pad_radius * self.dish_size
        self._td_pad.add(kv.graphics.Color(rgb=self.dish_color))
        self._td_pad.add(self._draw_circle(x, y, dish_radius))
        self._td_pad.add(kv.graphics.Color(rgb=self.pad_outline))
        self._td_pad.add(kv.graphics.Line(circle=(x, y, dish_radius)))

    def on_touch_down(self, touch):
        if self._active_touch:
            return super().on_touch_down(touch)

        if not self.collide_point(touch.x, touch.y):
            return super().on_touch_down(touch)

        self._active_touch = touch

        self._td_pt = Point(touch.pos)

        self._cal_sizes()  # calc pad size etc

        self._draw_pad(touch.x, touch.y)

        self.dispatch("on_engage")

        return True

    def _draw_stick(self, x, y):

        pad = self._td_pt
        self._dir_indicator.clear()

        self._dir_indicator.add(kv.graphics.Color(rgb=self.knob_outline))
        self._dir_indicator.add(
            kv.graphics.Line(circle=(pad.x, pad.y, self.shaft_width))
        )

        self._dir_indicator.add(kv.graphics.Color(rgb=self.shaft_color))

        self._dir_indicator.add(self._draw_circle(pad.x, pad.y, self.shaft_width))

        self._dir_indicator.add(
            kv.graphics.Line(points=[pad.x, pad.y, x, y], width=self.shaft_width)
        )

        self._dir_indicator.add(kv.graphics.Color(rgb=self.knob_color))
        self._dir_indicator.add(self._draw_circle(x, y, self.knob_radius))

        self._dir_indicator.add(kv.graphics.Color(rgb=self.knob_outline))
        self._dir_indicator.add(kv.graphics.Line(circle=(x, y, self.knob_radius)))

    def on_touch_move(self, touch):
        if touch is not self._active_touch:
            return super().on_touch_move(touch)

        rho = self._td_pt.distance_to(touch)
        theta = self._td_pt.radians_to(touch)

        if rho > self.pad_radius:
            x, y = self._td_pt.polar_from(theta, self.pad_radius)
            self._draw_stick(x, y)

            rho = 1.0
        else:
            self._draw_stick(touch.x, touch.y)
            if rho:
                rho = rho / self.pad_radius

        if self.trim:
            theta = theta + self.trim

            if theta > math.pi:
                theta = theta % math.pi
                theta = -math.pi + theta
            elif theta < -math.pi:
                theta = theta % -math.pi
                theta = math.pi + theta

        self.dispatch("on_move", theta, rho)
        return True

    def on_touch_up(self, touch):
        if touch is not self._active_touch:
            return super().on_touch_move(touch)

        self._active_touch = None
        self._td_pad.clear()
        self._dir_indicator.clear()

        self.dispatch("on_release")

        return True


class JoyApp(kv.app.App):
    def build(self):
        jp = JoyPad()
        jp.trim = -math.pi / 2
        jp.bind(on_engage=self.on_engage)
        jp.bind(on_move=self.on_move)
        jp.bind(on_release=self.on_release)

        return jp

    def on_engage(self, pad):
        print("engage!")
        return True

    def on_move(self, pad, theta, rho):
        print("{:3.2} : {:3.2}".format(theta, rho))
        return True

    def on_release(self, pad):
        print("release")
        return True


if __name__ == "__main__":
    JoyApp().run()
