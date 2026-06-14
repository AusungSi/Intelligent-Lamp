try:
    from machine import Pin, PWM
except ImportError:
    Pin = None
    PWM = None


_brightness_pwm = None
_warm_pwm = None
_cool_pwm = None
_last_control = None


def _init_pwm(pin_number, freq=1000):
    if pin_number is None or PWM is None or Pin is None:
        return None
    try:
        return PWM(Pin(int(pin_number)), freq=freq)
    except Exception as exc:
        print("PWM init failed on pin", pin_number, exc)
        return None


def init_lamp(config):
    global _brightness_pwm, _warm_pwm, _cool_pwm

    _brightness_pwm = _init_pwm(config.get("lamp_brightness_pin"))
    _warm_pwm = _init_pwm(config.get("lamp_warm_pin"))
    _cool_pwm = _init_pwm(config.get("lamp_cool_pin"))
    if _brightness_pwm or _warm_pwm or _cool_pwm:
        print("Lamp PWM initialized")
    else:
        print("Lamp PWM pins not configured, control will be logged only")


def _write_pwm(pwm, percent):
    if pwm is None:
        return
    value = max(0, min(100, int(percent)))
    duty = int(value * 1023 / 100)
    try:
        pwm.duty(duty)
    except AttributeError:
        pwm.duty_u16(int(value * 65535 / 100))


def apply_lamp_control(control):
    global _last_control

    if not control:
        return

    brightness = int(control.get("brightness", 68))
    color_temperature = int(control.get("color_temperature", 4100))
    scene_mode = control.get("scene_mode", "eye_care")

    _write_pwm(_brightness_pwm, brightness)

    # Simple two-channel CCT mix: 2700K is warm, 6500K is cool.
    cool_percent = int((color_temperature - 2700) * 100 / (6500 - 2700))
    cool_percent = max(0, min(100, cool_percent))
    warm_percent = 100 - cool_percent
    _write_pwm(_warm_pwm, int(brightness * warm_percent / 100))
    _write_pwm(_cool_pwm, int(brightness * cool_percent / 100))

    next_control = {
        "brightness": brightness,
        "color_temperature": color_temperature,
        "scene_mode": scene_mode,
    }
    if next_control != _last_control:
        print("Lamp control applied:", next_control)
        _last_control = next_control
