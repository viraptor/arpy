import arpy
import unittest
import os

class BSDExtendedNames(unittest.TestCase):
	def test_single_name(self):
		ar = arpy.Archive(os.path.join(os.path.dirname(__file__), 'bsd_single_name.ar'))
		ar.read_all_headers()
		self.assertEqual([b'a_very_long_name_for_the_gnu_type_header_so_it_can_overflow_the_standard_name_length'],
				list(ar.archived_files.keys()))
		self.assertEqual(2, len(ar.headers))
		ar.close()
	
	def test_multi_name_with_space(self):
		ar = arpy.Archive(os.path.join(os.path.dirname(__file__), 'bsd_multi_names.ar'))
		ar.read_all_headers()
		self.assertEqual([b'a_very_long_name_for_the_gnu_type_header_so_it_can_overflow_the_standard_name_length',
			b'a_very_long_name_for_the_gnu_type_header_so_it_can_overflow_the_standard_name_length_with_space '],
			sorted(ar.archived_files.keys()))
		self.assertEqual(3, len(ar.headers))
		ar.close()
	
	def test_mixed_names(self):
		ar = arpy.Archive(os.path.join(os.path.dirname(__file__), 'bsd_mixed.ar'))
		ar.read_all_headers()
		self.assertEqual([b'a_very_long_name_for_the_gnu_type_header_so_it_can_overflow_the_standard_name_length',
			b'short'],
			sorted(ar.archived_files.keys()))
		self.assertEqual(3, len(ar.headers))
		ar.close()
