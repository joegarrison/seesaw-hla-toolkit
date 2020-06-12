# High Level Analyzer
# For more information and documentation, please go to https://github.com/saleae/logic2-examples
from typing import Optional

from saleae.analyzers import HighLevelAnalyzer, AnalyzerFrame, StringSetting

base_format = {

}


class BaseI2CFilter(HighLevelAnalyzer):
    current_address: int
    target_address: int
    is_read: bool = False

    address_setting = StringSetting(label='Target Address (Dec or Hex)')

    result_types = {
        'start': {
            'format': 'Start'
        },
        'stop': {
            'format': 'Stop'
        },
        'address': {
            'format': '{{data.address}}, Read: {{data.read}}'
        },
        'data': {
            'format': '{{data.data}} {{data.error}}'
        }

    }

    def __init__(self):
        target_address = self.address_setting
        if not target_address:
            raise Exception('Target address is missing')

        base = 16 if target_address.startswith('0x') else 10
        try:
            self.target_address = int(target_address, base)
        except Exception as e:
            raise Exception('Invalid target address')

    def decode(self, frame):
        '''
        '''
        value = None
        if frame.type == 'address':
            self.is_read = frame.data['read']
            self.current_address = frame.data['address'][0]

        if self.current_address != None and self.current_address == self.target_address:
            value = ''
            if frame.type in ['address', 'data']:
                value = frame.data['address'][0] if frame.type == 'address' else frame.data['data'][0]

            return frame

        return None
