import datetime
import unittest
from dateutil import parser
from unittest import TestCase, main
from management.commands.utilities import *

class _TestUpdateDb(unittest.TestCase):

    def test_validate_dt_value(self):
        # test that a "proper" datetime does not throw exception
        test_time = datetime.datetime(2012, 3, 14, 0, 0, 0)
        result = validate_dt_value(test_time)
        self.assertEqual(None, result) 

        # test that ValueError is raised if microseconds is non-zero
        with self.assertRaises(ValueError) as context_manager:
            test_time = datetime.datetime(2012, 3, 14, 0, 0, 0, 100)
            validate_dt_value(test_time)

        ex = context_manager.exception
        self.assertEqual('Microseconds on datetime must ' \
            'be 0: 2012-03-14 00:00:00.000100', ex.message)

        # test that ValueError is raised if tzinfo is not None 
        with self.assertRaises(ValueError) as context_manager:
            test_time = parser.parse("2012-02-21T10:57:47-05:00") 
            validate_dt_value(test_time)

        ex = context_manager.exception
        self.assertEqual('Tzinfo on datetime must be None: ' \
            '2012-02-21 10:57:47-05:00', ex.message)

    def test_transform_date(self):
        # transform an ISO 8601 string that represents 2/21/2012 at 10:57:47
        # with a 5 hour offset 
        d = transform_date("2012-02-21T10:57:47-05:00")
        # expect to recieve a string formatted with just YYYY-MM-DD HH:MM
        self.assertEqual("2012-02-21 10:57", d) 
         
    def test_get_time_range(self):
       # if we create a start date of 3/14
       start_date = datetime.datetime(2012, 3, 14, 0, 0, 0) 
       # our expected start and end dates are as follows
       expected_start_date = start_date - datetime.timedelta(days=1)
       expected_end_date = datetime.datetime(2012, 3, 14, 0, 0, 0) 
       # call the method and assert we get what we expect
       start, end = get_time_range(start_date)
       self.assertEqual(end, expected_end_date) 
       self.assertEqual(start, expected_start_date) 

       # same as above but make sure that a start_date passed in
       # as NOT midnight gets set to midnight 
       start_date = datetime.datetime(2012, 3, 14, 1, 30, 30) 
       # our expected start and end dates are as follows
       expected_start_date = start_date.replace(hour=0, minute=0, second=0, 
           microsecond=0) - datetime.timedelta(days=1)
       expected_end_date = datetime.datetime(2012, 3, 14, 0, 0, 0) 
       # call the method and assert we get what we expect
       start, end = get_time_range(start_date)
       self.assertEqual(end, expected_end_date) 
       self.assertEqual(start, expected_start_date) 

       # same as above but pass None and check that default
       # behavior works as intended 
       # our expected start and end dates are as follows
       expected_end_date = datetime.datetime.utcnow().replace(hour=0, minute=0,
           second=0, microsecond=0) - datetime.timedelta(days=1)
       expected_start_date = expected_end_date - datetime.timedelta(days=1)
       # call the method and assert we get what we expect
       start, end = get_time_range()
       self.assertEqual(end, expected_end_date) 
       self.assertEqual(start, expected_start_date) 

if __name__ == '__main__':
	suite = unittest.TestLoader().loadTestsFromTestCase(_TestUpdateDb)
	unittest.TextTestRunner(verbosity=2).run(suite)
