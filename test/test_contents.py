import arpy
import unittest, os

class ArContents(unittest.TestCase):
	def test_archive_contents(self):
		ar = arpy.Archive(os.path.join(os.path.dirname(__file__), 'contents.ar'))
		ar.read_all_headers()
		f1_contents = ar.archived_files['file1'].read()
		f2_contents = ar.archived_files['file2'].read()
		self.assertEqual(b'test_in_file_1\n', f1_contents)
		self.assertEqual(b'test_in_file_2\n', f2_contents)
		ar.close()

	def test_content_seeking(self):
		ar = arpy.Archive(os.path.join(os.path.dirname(__file__), 'contents.ar'))
		ar.read_all_headers()

		f1 = ar.archived_files['file1']
		contents_before = f1.read()
		f1.seek(0)
		contents_after = f1.read()
		f1.seek(3)
		contents_shifted = f1.read()
		
		self.assertEqual(contents_before, contents_after)
		self.assertEqual(contents_before[3:], contents_shifted)
		ar.close()
