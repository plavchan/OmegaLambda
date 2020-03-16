from main.common.IO.json_reader import Reader
from main.common.datatype.object_reader import ObjectReader
import unittest
import datetime

# NOTE: There is a typo in the username on ops: It's called "GMU Observtory1" instead of "GMU Observatory1"
test_reader = Reader(r'c:\users\gmu observtory1\-omegalambda\resources\test.json')
object_reader = ObjectReader(test_reader.str, 'observation_ticket')

class ObsTester(unittest.TestCase):
    
    def test_attributes(self):
        global object_reader 
        self.assertEqual(object_reader.ticket.name, 'M41_1')
        self.assertEqual(object_reader.ticket.start_time, datetime.datetime(2020, 1, 12, 18, 0, 0))
        self.assertEqual(object_reader.ticket.num, 100)
        self.assertFalse(object_reader.ticket.self_guide)
    
    def test_datatypes(self):
        global object_reader
        self.assertTrue(type(object_reader.ticket.name) is str)
        self.assertTrue(type(object_reader.ticket.start_time is str))
        self.assertTrue(type(object_reader.ticket.num) is int)
        self.assertTrue(type(object_reader.ticket.self_guide) is bool)

test_reader_fw = Reader(r'c:\users\gmu observtory1\-omegalambda\resources\test_fw.json')
object_reader_fw = ObjectReader(test_reader_fw.str, 'filter_wheel')

class FWTester(unittest.TestCase):
    
    def test_attributes(self):
        global object_reader_fw
        self.assertEqual(object_reader_fw.ticket.position_1, 'uv')
        self.assertEqual(object_reader_fw.ticket.position_8, 'Ha')
    
    def test_datatypes(self):
        global object_reader_fw
        self.assertTrue(type(object_reader_fw.ticket.position_1) is str)
        self.assertTrue(type(object_reader_fw.ticket.position_8) is str)
        
if __name__ == '__main__':
    unittest.main()
        
# python -m unittest main.drivers.json_test_driver.ObsTester
# c:\users\gmuobservatory\-omegalambda\resources\test.json
