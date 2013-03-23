import arpy
import io
import unittest, os

class SimpleNames(unittest.TestCase):
	def test_single_name(self):
		ar = arpy.Archive(os.path.join(os.path.dirname(__file__), 'normal.ar'))
		ar.read_all_headers()
		self.assertEqual([b'short'],
				list(ar.archived_files.keys()))
		self.assertEqual(1, len(ar.headers))
		ar.close()

	def test_header_description(self):
		ar = arpy.Archive(os.path.join(os.path.dirname(__file__), 'normal.ar'))
		header = ar.read_next_header()
		self.assertTrue(repr(header).startswith('<ArchiveFileHeader'))
		ar.close()
	
	def test_empty_ar(self):
		ar = arpy.Archive(os.path.join(os.path.dirname(__file__), 'empty.ar'))
		ar.read_all_headers()
		self.assertEqual([],
				list(ar.archived_files.keys()))
		self.assertEqual(0, len(ar.headers))
		ar.close()

	def test_fileobj(self):
		data = open(os.path.join(os.path.dirname(__file__), 'normal.ar'), "rb").read()
		ar = arpy.Archive(fileobj=io.BytesIO(data))
		ar.read_all_headers()
		self.assertEqual([b'short'],
				list(ar.archived_files.keys()))
		self.assertEqual(1, len(ar.headers))
		ar.close()
