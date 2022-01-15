class NegativeValueException(Exception):
    pass

def set_robot_power(value):
    if value < 0:
        raise NegativeValueException('Введите число, которое больше нуля!')

set_robot_power(-1)