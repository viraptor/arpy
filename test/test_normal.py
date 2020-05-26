import arpy
import io
import unittest
import os

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

	def test_symbols(self):
		ar = arpy.Archive(os.path.join(os.path.dirname(__file__), 'sym.ar'))
		syms = ar.read_next_header()
		self.assertEqual(arpy.HEADER_GNU_SYMBOLS, syms.type)
		self.assertEqual(4, syms.size)
		ao = ar.read_next_header()
		self.assertEqual(arpy.HEADER_NORMAL, ao.type)
		self.assertEqual(0, ao.size)
		self.assertEqual(b"a.o", ao.name)
		ar.close()

	def test_windows(self):
		ar = arpy.Archive(os.path.join(os.path.dirname(__file__), 'windows.ar'))
		file_header = ar.read_next_header()
		self.assertIsNone(file_header.gid)
		self.assertIsNone(file_header.uid)
		ar.close()

	def test_fileobj(self):
		data = open(os.path.join(os.path.dirname(__file__), 'normal.ar'), "rb").read()
		ar = arpy.Archive(fileobj=io.BytesIO(data))
		ar.read_all_headers()
		self.assertEqual([b'short'],
				list(ar.archived_files.keys()))
		self.assertEqual(1, len(ar.headers))
		ar.close()


class ArchiveIteration(unittest.TestCase):
	def test_iteration(self):
		ar = arpy.Archive(os.path.join(os.path.dirname(__file__), 'normal.ar'))
		ar_iterator = iter(ar)
		short = ar_iterator.next()
		self.assertEqual(b'short', short.header.name)
		self.assertRaises(StopIteration, ar_iterator.next)
		ar.close()
