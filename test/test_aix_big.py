"""Tests for archives in AIX Big Format."""
from cStringIO import StringIO
import arpy
import random
import string
import unittest


class AIXBigFormatMixin(object):
	"""Common code for testing AIX big format archive."""

	def getFileWithContent(self, content):
		"""Return a file like object with `content`."""
		return StringIO(content)

	def getGlobalHeaderContent(self, first_member=None, last_member=None):
		"""Return a valid content for global header with random data."""
		if first_member is None:
			first_member = random.randint(128, 10000)

		if last_member is None:
			last_member = random.randint(128, 10000)

		content = (
			'<bigaf>\n'
			'91268               '
			'91458               '
			'93664               '
			'%-20d'
			'%-20d'
			'234                 '
			) % (first_member, last_member)
		return content

	def getFileHeaderInitialContent(self,
			content_length=None, filename_length=None, next_member=None):
		"""Return a file header initial content with random data."""

		if content_length is None:
			content_length = random.randint(1, 43563)
		if filename_length is None:
			filename_length = random.randint(1, 255)
		if next_member is None:
			next_member = random.randint(1, 43563)

		initial_content = (
			'%-20d'
			'%-20d'
			'123                 '
			'1087823288  '
			'300         '
			'301         '
			'640         '
			'%-4d'
			) % (content_length, next_member, filename_length)
		return initial_content

	def getRandomString(self,
			size=12, chars=string.ascii_uppercase + string.digits):
		"""Return a string with random data."""
		return ''.join(random.choice(chars) for x in range(size))

	def getFileEntry(self, name=None, content=None, next_member=None):
		"""Return raw content for a file entry from the archive."""
		if name is None:
			name = self.getRandomString()

		if content is None:
			content = self.getRandomString()

		initial_content = self.getFileHeaderInitialContent(
			content_length=len(content),
			filename_length=len(name),
			next_member=next_member,
			)

		pad = ''
		if  len(name) % 2:
			pad = '\0'

		return (
			initial_content +
			name + pad + '`\n' +
			content)


class TestArchiveAIXBigFormat(unittest.TestCase, AIXBigFormatMixin):
	"""Test for loading archives in AIX big format."""

	def test_init_bad_format(self):
		"""Raise an error when file is not AIX big format."""
		content = self.getFileWithContent("some bad content")

		with self.assertRaises(arpy.ArchiveFormatError):
			arpy.AIXBigArchive(fileobj=content)

	def test_init_good_format(self):
		"""It can be initialized with a valid AIX big format file."""
		first_member = 123
		content = self.getFileWithContent(
			self.getGlobalHeaderContent(first_member=first_member))

		archive = arpy.AIXBigArchive(fileobj=content)

		self.assertIsNotNone(archive.global_header)
		self.assertEqual(first_member, archive.global_header.first_member)
		self.assertEqual(first_member, archive.next_header_offset)
		self.assertEqual([], archive.headers)
		self.assertEqual({}, archive.archived_files)
		# The cursor is now at the end of the header.
		self.assertEqual(archive.global_header.LENGTH, archive.position)

	def test_read_next_header_end_of_list(self):
		"""None is returned when there is no more a next header."""
		content = self.getFileWithContent(self.getGlobalHeaderContent())
		archive = arpy.AIXBigArchive(fileobj=content)
		archive.next_header_offset = 0

		result = archive.read_next_header()

		self.assertIsNone(result)

	def test_read_next_header_start(self):
		"""
		After archive is initialized, it will read the first member and will
		update the next member pointer.

		"""
		# Add a gap after global header to test seeking.
		gap = 'Xdssd'
		first_member = 128 + len(gap)
		next_member = 1024
		file_content = 'ABCDE-MARKER'
		content = self.getFileWithContent(
			self.getGlobalHeaderContent(first_member=first_member) +
			gap +
			self.getFileEntry(next_member=next_member, content=file_content)
			)
		archive = arpy.AIXBigArchive(fileobj=content)

		file_header = archive.read_next_header()

		self.assertEqual(next_member, archive.next_header_offset)
		self.assertIn(file_header, archive.headers)
		data = archive.archived_files[file_header.name]
		self.assertIsNotNone(data)
		self.assertEqual(file_content, data.read())

	def test_read_next_header_end_of_file(self):
		"""
		Return None when we are at the end of the file.

		"""
		content = self.getFileWithContent(
			self.getGlobalHeaderContent() +
			self.getFileEntry()
			)
		archive = arpy.AIXBigArchive(fileobj=content)
		archive.next_header_offset = len(content.getvalue())

		result = archive.read_next_header()

		self.assertIsNone(result)
		self.assertEqual([], archive.headers)

	def test_read_next_header_last_header(self):
		"""
		Set next_member to 0 when we have read the last member.

		"""
		first_member = 128
		# Use event size to avoid padding
		first_name = self.getRandomString(size=6)
		last_name = self.getRandomString()
		first_content = self.getRandomString()
		next_member = 128 + 112 + len(first_name) + 2 + len(first_content)
		content = self.getFileWithContent(
			self.getGlobalHeaderContent(
				first_member=first_member, last_member=next_member) +
			self.getFileEntry(
				name=first_name,
				next_member=next_member,
				content=first_content,
				) +
			self.getFileEntry(name=last_name)
			)
		archive = arpy.AIXBigArchive(fileobj=content)
		# Read first header.
		archive.read_next_header()

		# Read last header.
		result = archive.read_next_header()
		self.assertIsNotNone(result)
		self.assertEqual(last_name, result.name)

		# After last header.
		result = archive.read_next_header()
		self.assertIsNone(result)


class TestAIXBigGlobalHeader(unittest.TestCase):
	"""Tests for global header or AIX big format archive."""

	def test_short_header(self):
		"""An error is raised when header is too short."""
		with self.assertRaises(arpy.ArchiveFormatError) as context:
			arpy.AIXBigGlobalHeader('<bigaf>\nshort_header')

		self.assertIn('file to short', context.exception.message)

	def test_bad_magic_marker(self):
		"""An error is raised when header does not starts with a marker."""
		with self.assertRaises(arpy.ArchiveFormatError) as context:
			# Create a file which can theoretically accommodate a header.
			arpy.AIXBigGlobalHeader('a' * (arpy.AIXBigGlobalHeader.LENGTH + 1))

		self.assertIn('not an AIX big', context.exception.message)

	def test_parse_content(self):
		"""Global header content is parsed for all fields."""
		content = (
			'<bigaf>\n'
			'91268               '
			'91458               '
			'93664               '
			'136                 '
			'43270               '
			'234                 '
			)
		global_header = arpy.AIXBigGlobalHeader(content)

		self.assertEqual(91268, global_header.members)
		self.assertEqual(91458, global_header.global_symbol)
		self.assertEqual(93664, global_header.global_symbol_64)
		self.assertEqual(136, global_header.first_member)
		self.assertEqual(43270, global_header.last_member)
		self.assertEqual(234, global_header.first_free_member)


class TestAIXBigFileHeader(unittest.TestCase, AIXBigFormatMixin):
	"""Test for a file header from an AIX big format archive."""

	def test_short_header(self):
		"""An error is raised if header is too short."""
		with self.assertRaises(arpy.ArchiveFormatError) as context:
			arpy.AIXBigFileHeader('short-header', None)

		self.assertIn('file header too short', context.exception.message)

	def test_initial_parse(self):
		"""
		It is initialized with the minimum fixed header size which does not
		contains the variable file name.

		"""
		offset = random.randint(128, 1023)
		initial_content = (
			'1216                '
			'1466                '
			'123                 '
			'1087823288  '
			'300         '
			'301         '
			'640         '
			'6   '
			)
		header = arpy.AIXBigFileHeader(initial_content, offset)

		# Check parded data.
		self.assertEqual(1216, header.size)
		self.assertEqual(1466, header.next_member)
		self.assertEqual(123, header.previous_member)
		self.assertEqual(1087823288, header.timestamp)
		self.assertEqual(300, header.uid)
		self.assertEqual(301, header.gid)
		self.assertEqual(416, header.mode)  # Parsed in octal.
		self.assertEqual(6, header.filename_length)

		# Check other members.
		self.assertEqual(arpy.HEADER_NORMAL, header.type)
		self.assertEqual(6 + 2, header.remaining_header_length)

		self.assertEqual(112 + 6 + 2, header.relative_file_offset)
		self.assertEqual(offset + 112 + 6 + 2, header.file_offset)

	def test_remaining_header_length_already_aligned(self):
		"""No padding is added if header ends at an aligned address."""
		initial_content = self.getFileHeaderInitialContent(filename_length=6)
		header = arpy.AIXBigFileHeader(initial_content, None)

		self.assertEqual(6 + 2, header.remaining_header_length)

	def test_remaining_header_length_already_unaligned(self):
		"""
		A 1 byte padding is added to align the header ending / file content
		start at 2 bytes offset.

		"""
		initial_content = self.getFileHeaderInitialContent(filename_length=7)
		header = arpy.AIXBigFileHeader(initial_content, None)

		self.assertEqual(7 + 1 + 2, header.remaining_header_length)

	def test_updateRemainingHeader_short(self):
		"""An error is raised if content is too short."""
		initial_content = self.getFileHeaderInitialContent(filename_length=45)
		header = arpy.AIXBigFileHeader(initial_content, None)

		with self.assertRaises(arpy.ArchiveFormatError) as context:
			header.updateRemainingHeader('short-filename')

		self.assertIn('file header end too short', context.exception.message)

	def test_updateRemainingHeader_bad_end_marker(self):
		"""An error is raised when the file header end marker is not found."""
		initial_content = self.getFileHeaderInitialContent(filename_length=5)
		header = arpy.AIXBigFileHeader(initial_content, None)

		with self.assertRaises(arpy.ArchiveFormatError) as context:
			header.updateRemainingHeader('12345\nAB')

		self.assertIn('bad ending for file header', context.exception.message)

	def test_updateRemainingHeader_ok(self):
		"""Filename is updated from remaining header."""
		initial_content = self.getFileHeaderInitialContent(filename_length=5)
		header = arpy.AIXBigFileHeader(initial_content, None)

		header.updateRemainingHeader('12345\0`\n')

		self.assertEqual('12345', header.name)
