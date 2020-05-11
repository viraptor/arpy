import arpy
import unittest
import os
import io

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
		pos = self.f1.seek(0)
		self.assertEqual(pos, 0)
		contents_after = self.f1.read()
		pos = self.f1.seek(3)
		self.assertEqual(pos, 3)
		contents_shifted = self.f1.read()
		self.assertEqual(contents_before, contents_after)
		self.assertEqual(contents_before[3:], contents_shifted)

	def test_seek_relative(self):
		contents_before = self.f1.read()
		self.f1.seek(1)
		pos = self.f1.seek(1, 1)
		self.assertEqual(pos, 2)
		contents_after = self.f1.read()
		self.assertEqual(contents_before[2:], contents_after)

	def test_seek_from_end(self):
		contents_before = self.f1.read()
		pos = self.f1.seek(-4, 2)
		self.assertEqual(pos, 11)
		contents_after = self.f1.read()
		self.assertEqual(contents_before[-4:], contents_after)

	def test_seek_failure(self):
		self.assertRaises(arpy.ArchiveAccessError, self.f1.seek, 10, 10)

	def test_seek_position_failure(self):
		self.assertRaises(arpy.ArchiveAccessError, self.f1.seek, -1)

	def test_check_seekable(self):
		self.assertTrue(self.f1.seekable())


class NonSeekableIO(io.BytesIO):
	def seek(self, *args):
		raise Exception("Not seekable")

	def seekable(self):
		return False

	def force_seek(self, *args):
		io.BytesIO.seek(self, *args)


class ArContentsNoSeeking(unittest.TestCase):
	def setUp(self):
		big_archive = NonSeekableIO()
		big_archive.write(b"!<arch>\n")
		big_archive.write(b"file1/          1364071329  1000  100   100644  5000      `\n")
		big_archive.write(b" "*5000)
		big_archive.write(b"file2/          1364071329  1000  100   100644  2         `\n")
		big_archive.write(b"xx")
		big_archive.force_seek(0)
		self.big_archive = big_archive

	def test_stream_read(self):
		# make sure all contents can be read without seeking
		ar = arpy.Archive(fileobj=self.big_archive)
		f = ar.next()
		contents = f.read()
		self.assertEqual(b'file1', f.header.name)
		self.assertEqual(b' '*5000, contents)
		f = ar.next()
		contents = f.read()
		self.assertEqual(b'file2', f.header.name)
		self.assertEqual(b'xx', contents)
		ar.close()

	def test_stream_skip_file(self):
		# make sure skipping contents is possible without seeking
		ar = arpy.Archive(fileobj=self.big_archive)
		f = ar.next()
		self.assertEqual(b'file1', f.header.name)
		f = ar.next()
		contents = f.read()
		self.assertEqual(b'file2', f.header.name)
		self.assertEqual(b'xx', contents)
		ar.close()

	def test_seek_fail(self):
		ar = arpy.Archive(fileobj=self.big_archive)
		f1 = ar.next()
		ar.next()
		self.assertRaises(arpy.ArchiveAccessError, f1.read)
		ar.close()

	def test_check_seekable(self):
		ar = arpy.Archive(fileobj=self.big_archive)
		f1 = ar.next()
		self.assertFalse(f1.seekable())
		ar.close()
