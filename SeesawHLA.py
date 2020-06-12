# High Level Analyzer
# For more information and documentation, please go to https://github.com/saleae/logic2-examples
from typing import List
from enum import Enum
from base_i2c_filter import BaseI2CFilter
from saleae.analyzers import HighLevelAnalyzer, AnalyzerFrame, StringSetting, ChoicesSetting
from saleae.data import GraphTime

base_addresses = {
    0x00: 'STATUS_BASE',
    0x01: 'GPIO_BASE',
    0x02: 'SERCOM0_BASE',
    0x08: 'TIMER_BASE',
    0x09: 'ADC_BASE',
    0x0A: 'DAC_BASE',
    0x0B: 'INTERRUPT_BASE',
    0x0C: 'DAP_BASE',
    0x0D: 'EEPROM_BASE',
    0x0E: 'NEOPIXEL_BASE',
    0x0F: 'TOUCH_BASE',
    0x10: 'KEYPAD_BASE',
    0x11: 'ENCODER_BASE',
}


class Action(Enum):
    Temperature = 'Temperature'
    Capacitive = 'Capacitive'
    HW_ID = 'HW_ID'
    VERSION = 'VERSION'
    OPTIONS = 'OPTIONS'
    SWRST = 'SWRST'


actions = {
    'TOUCH_BASE': {
        0x10: Action.Capacitive,
    },
    'STATUS_BASE': {
        0x01: Action.HW_ID,
        0x02: Action.VERSION,
        0x03: Action.OPTIONS,
        0x04: Action.Temperature,
        0x7F: Action.SWRST,
    }
}


FORMATTED_ACTIONS = [Action.Temperature]


class Hla(BaseI2CFilter):
    read_transaction: AnalyzerFrame = None
    last_frame: AnalyzerFrame = None
    write_transaction: AnalyzerFrame = None
    settings = dict()
    action: Action = None
    base_action: str = ''

    NOT_FOUND = 'NotFound'

    temp_units_setting = ChoicesSetting(label='Temp Units', choices=('C', 'F'))

    result_types = {
        'default': {
            'format': '{{data.value}}'
        }
    }

    def __init__(self):
        super().__init__()
        self.result_types[Action.Temperature.name] = {
            'format': '{{data.value}} ' + self.temp_units_setting
        }

    def get_action_name(self):
        return self.action.name if self.action else 'default'

    def format_read_value(self):
        if self.action == Action.Temperature:
            value = self.read_transaction.data['value']
            value = value / 2 ** 16
            if self.temp_units_setting == 'F':
                value = value * (9 / 5) + 32
            self.read_transaction.data['value'] = '{:.2f}'.format(value)

    def decode(self, frame):
        frame = super().decode(frame)
        if not frame:
            return

        # Handle new transactions (Read or Write)
        if frame.type == 'address':
            action_name = self.get_action_name()
            new_frame = None
            if self.read_transaction:
                self.read_transaction.end_time = self.last_frame.end_time
                self.format_read_value()
                new_frame = self.read_transaction

            elif self.write_transaction:
                self.write_transaction.end_time = self.last_frame.end_time
                self.write_transaction.data['value'] = action_name
                new_frame = self.write_transaction

            value = frame.data['address']

            if self.is_read:
                if (self.write_transaction):
                    frame_type = self.action.name if self.action in FORMATTED_ACTIONS else 'default'
                    self.read_transaction = AnalyzerFrame(
                        type=frame_type, start_time=frame.start_time, end_time=frame.end_time, data={"value": 0})
                self.write_transaction = None
            else:
                self.write_transaction = AnalyzerFrame(
                    type='default', start_time=frame.start_time, end_time=frame.end_time, data={})
                self.read_transaction = None
                self.base_action = None
                self.action = None
            return new_frame

        # Handle the data
        elif frame.type == 'data':
            value = frame.data['data'][0]
            if self.is_read:
                if self.read_transaction:
                    self.read_transaction.data['value'] = (self.read_transaction.data['value'] << 8) | value
            else:
                if not self.write_transaction:
                    # Handle the case where we missed the address frame
                    return None
                if not self.base_action:
                    self.base_action = base_addresses.get(value, Hla.NOT_FOUND)
                elif self.base_action != Hla.NOT_FOUND:
                    current_actions = actions.get(self.base_action)
                    if current_actions:
                        self.action = current_actions.get(value)

            self.last_frame = frame
        else:
            return None
