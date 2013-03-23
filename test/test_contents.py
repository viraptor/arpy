import arpy
import unittest, os

class ArContents(unittest.TestCase):
	def test_archive_contents(self):
		ar = arpy.Archive(os.path.join(os.path.dirname(__file__), 'contents.ar'))
		ar.read_all_headers()
		f1_contents = ar.archived_files[b'file1'].read()
		f2_contents = ar.archived_files[b'file2'].read()
		self.assertEqual(b'test_in_file_1\n', f1_contents)
		self.assertEqual(b'test_in_file_2\n', f2_contents)
		ar.close()


class ArContentsSeeking(unittest.TestCase):
	def setUp(self):
		self.ar = arpy.Archive(os.path.join(os.path.dirname(__file__), 'contents.ar'))
		self.ar.read_all_headers()

		self.f1 = self.ar.archived_files[b'file1']

	def tearDown(self):
		self.ar.close()

	def test_content_opens_at_zero(self):
		self.assertEqual(0, self.f1.tell())

	def test_seek_absolute(self):
		contents_before = self.f1.read()
		self.f1.seek(0)
		contents_after = self.f1.read()
		self.f1.seek(3)
		contents_shifted = self.f1.read()
		self.assertEqual(contents_before, contents_after)
		self.assertEqual(contents_before[3:], contents_shifted)

	def test_seek_relative(self):
		contents_before = self.f1.read()
		self.f1.seek(1)
		self.f1.seek(1, 1)
		contents_after = self.f1.read()
		self.assertEqual(contents_before[2:], contents_after)

	def test_seek_from_end(self):
		contents_before = self.f1.read()
		self.f1.seek(-4, 2)
		contents_after = self.f1.read()
		self.assertEqual(contents_before[-4:], contents_after)

	def test_seek_failure(self):
		self.assertRaises(arpy.ArchiveAccessError, self.f1.seek, 10, 10)

	def test_seek_position_failure(self):
		self.assertRaises(arpy.ArchiveAccessError, self.f1.seek, -1)
