from vesper.tests.test_case import TestCase
from vesper.util.preference_manager import PreferenceManager
import vesper.tests.test_utils as test_utils


_DATA_DIR_PATH = test_utils.get_test_data_dir_path(__file__)


class PreferenceManagerTests(TestCase):
    
    
    def setUp(self):
        self.manager = PreferenceManager(_DATA_DIR_PATH)

        
    def test_get(self):
        
        p = self.manager.preferences
        
        cases = (
            ('one', 1),
            ('category_a.two', 2),
            ('category_a.three', 'three'),
            ('category_a.category_b.forty_five', 45),
            ('category_a.category_b.fifty six', 56),
            ('category_a.category_b', {'forty_five': 45, 'fifty six': 56})
        )
        
        for name, value in cases:
            self.assertTrue(name in p)
            self.assertEqual(p[name], value)
            self.assertEqual(p.get(name), value)


    def test_get_of_nonexistent_preferences(self):
        
        p = self.manager.preferences
        
        cases = (
            'bobo',
            'category_a.bobo'
        )
        
        for name in cases:
            self.assertFalse(name in p)
            self.assertRaises(KeyError, p.__getitem__, name)
            self.assertIsNone(p.get(name))
            self.assertEqual(p.get(name, 10), 10)
            
            
#     def test_nonexistent_preference_file(self):
#         p = PreferenceManager('nonexistent').preferences
#         self.assertEqual(len(p), 0)