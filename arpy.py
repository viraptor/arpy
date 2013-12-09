# -*- coding: utf-8 -*-
#
# Copyright 2011 Stanisław Pitucha. All rights reserved.
# Copyright 2013 Helmut Grohne. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are
# permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright notice, this list of
#       conditions and the following disclaimer.
#
#    2. Redistributions in binary form must reproduce the above copyright notice, this list
#       of conditions and the following disclaimer in the documentation and/or other materials
#       provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY Stanisław Pitucha ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL Stanisław Pitucha OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are those of the
# authors and should not be interpreted as representing official policies, either expressed
# or implied, of Stanisław Pitucha.
#

"""
arpy module can be used for reading `ar` files' headers, as well as accessing
the data contained in the archive. Archived files are accessible via file-like
objects.
Support for both GNU and BSD extended length filenames is included.

In order to read the file, create a new proxy with:
ar = arpy.Archive('some_ar_file')
ar.read_all_headers()

The list of file names can be listed through:
ar.archived_files.keys()

Files themselves can be opened by getting the value of:
f = ar.archived_files['filename']

and read through:
f.read([length])

random access through seek and tell functions is supported on the archived files
"""

import struct

HEADER_BSD = 1
HEADER_GNU = 2
HEADER_GNU_TABLE = 3
HEADER_GNU_SYMBOLS = 4
HEADER_NORMAL = 5
HEADER_TYPES = {
		HEADER_BSD: 'BSD',
		HEADER_GNU: 'GNU', HEADER_GNU_TABLE: 'GNU_TABLE',
		HEADER_GNU_SYMBOLS: 'GNU_SYMBOLS',
		HEADER_NORMAL: 'NORMAL'}

GLOBAL_HEADER_LEN = 8
HEADER_LEN = 60

class ArchiveFormatError(Exception):
	""" Raised on problems with parsing the archive headers """
	pass
class ArchiveAccessError(IOError):
	""" Raised on problems with accessing the archived files """
	pass

class ArchiveFileHeader(object):
	""" File header of an archived file, or a special data segment """

	def __init__(self, header, offset):
		""" Creates a new header from binary data starting at a specified offset """
		name, timestamp, uid, gid, mode, size, magic = struct.unpack(
				"16s 12s 6s 6s 8s 10s 2s", header)
		if magic != b"\x60\x0a":
			raise ArchiveFormatError("file header magic doesn't match")

		if name.startswith(b"#1/"):
			self.type = HEADER_BSD
		elif name.startswith(b"//"):
			self.type = HEADER_GNU_TABLE
		elif name.strip() == b"/":
			self.type = HEADER_GNU_SYMBOLS
		elif name.startswith(b"/"):
			self.type = HEADER_GNU
		else:
			self.type = HEADER_NORMAL

		try:
			self.size = int(size)

			if self.type in (HEADER_NORMAL, HEADER_BSD, HEADER_GNU):
				self.timestamp = int(timestamp)
				self.uid = int(uid)
				self.gid = int(gid)
				self.mode = int(mode, 8)

		except ValueError as err:
			raise ArchiveFormatError(
					"cannot convert file header fields to integers", err)

		self.offset = offset
		name = name.rstrip()
		if len(name) > 1:
			name = name.rstrip(b'/')

		if self.type == HEADER_NORMAL:
			self.name = name
			self.file_offset = offset + HEADER_LEN
		else:
			self.name = None
			self.proxy_name = name
			self.file_offset = None

	def __repr__(self):
		""" Creates a human-readable summary of a header """
		return '''<ArchiveFileHeader: "%s" type:%s size:%i>''' % (self.name,
				HEADER_TYPES[self.type], self.size)

class ArchiveFileData(object):
	""" File-like object used for reading an archived file """

	def __init__(self, ar_obj, header):
		"""
		Creates a new proxy for the archived file, reusing the archive's file descriptor
		"""
		self.header = header
		self.arobj = ar_obj
		self.last_offset = 0

	def read(self, size = None):
		""" Reads the data from the archived file, simulates file.read """
		if size is None:
			size = self.header.size

		if self.header.size < self.last_offset + size:
			size = self.header.size - self.last_offset

		self.arobj._seek(self.header.file_offset + self.last_offset)
		data = self.arobj._read(size)
		if len(data) < size:
			raise ArchiveAccessError("incorrect archive file")

		self.last_offset += size
		return data

	def tell(self):
		""" Returns the position in archived file, simulates file.tell """
		return self.last_offset

	def seek(self, offset, whence = 0):
		""" Sets the position in archived file, simulates file.seek """
		if whence == 0:
			pass # absolute
		elif whence == 1:
			offset += self.last_offset
		elif whence == 2:
			offset += self.header.size
		else:
			raise ArchiveAccessError("invalid argument")
		
		if offset < 0 or offset > self.header.size:
			raise ArchiveAccessError("incorrect file position")
		self.last_offset = offset

class Archive(object):
	""" Archive object allowing reading of *.ar files """
	def __init__(self, filename=None, fileobj=None):
		self.headers = []
		self.file = fileobj or open(filename, "rb")
		self.position = 0
		self._detect_seekable()
		if self._read(GLOBAL_HEADER_LEN) != b"!<arch>\n":
			raise ArchiveFormatError("file is missing the global header")
		
		self.next_header_offset = GLOBAL_HEADER_LEN
		self.gnu_table = None
		self.archived_files = {}

	def _detect_seekable(self):
		if hasattr(self.file, 'seekable'):
			self.seekable = self.file.seekable()
		else:
			try:
				# .tell() will raise an exception as well
				self.file.tell()
				self.seekable = True
			except:
				self.seekable = False

	def _read(self, length):
		data = self.file.read(length)
		self.position += len(data)
		return data

	def _seek(self, offset):
		if self.seekable:
			self.file.seek(offset)
			self.position = self.file.tell()
		elif offset < self.position:
			raise ArchiveAccessError("cannot go back when reading archive from a stream")
		else:
			# emulate seek
			while self.position < offset:
				if not self._read(min(4096, offset - self.position)):
					# reached EOF before target offset
					return

	def _read_file_header(self, offset):
		""" Reads and returns a single new file header """
		self._seek(offset)

		header = self._read(HEADER_LEN)

		if len(header) == 0:
			return None
		if len(header) < HEADER_LEN:
			raise ArchiveFormatError("file header too short")
		
		file_header = ArchiveFileHeader(header, offset)
		if file_header.type == HEADER_GNU_TABLE:
			self.__read_gnu_table(file_header.size)
			
		add_len = self.__fix_name(file_header)
		file_header.file_offset = offset + HEADER_LEN + add_len

		if offset == self.next_header_offset:
			new_offset = file_header.file_offset + file_header.size
			self.next_header_offset = Archive._pad2(new_offset)

		return file_header

	def __read_gnu_table(self, size):
		""" Reads the table of filenames specific to GNU ar format """
		table_string = self._read(size)
		if len(table_string) != size:
			raise ArchiveFormatError("file too short to fit the names table")

		self.gnu_table = {}
		
		position = 0
		for filename in table_string.split(b"\n"):
			self.gnu_table[position] = filename[:-1] # remove trailing '/'
			position += len(filename) + 1

	def __fix_name(self, header):
		"""
		Corrects the long filename using the format-specific method.
		That means either looking up the name in GNU filename table, or
		reading past the header in BSD ar files.
		"""
		if header.type == HEADER_NORMAL:
			pass

		elif header.type == HEADER_BSD:
			filename_len = Archive.__get_bsd_filename_len(header.proxy_name)

			# BSD format includes the filename in the file size
			header.size -= filename_len

			self._seek(header.offset + HEADER_LEN)
			header.name = self._read(filename_len)
			return filename_len

		elif header.type == HEADER_GNU_TABLE:
			header.name = "*GNU_TABLE*"

		elif header.type == HEADER_GNU:
			gnu_position = int(header.proxy_name[1:])
			if gnu_position not in self.gnu_table:
				raise ArchiveFormatError("file references a name not present in the index")
			header.name = self.gnu_table[gnu_position]
			
		elif header.type == HEADER_GNU_SYMBOLS:
			pass
		
		return 0

	@staticmethod
	def _pad2(num):
		""" Returns a 2-aligned offset """
		if num % 2 == 0:
			return num
		else:
			return num+1

	@staticmethod
	def __get_bsd_filename_len(name):
		""" Returns the length of the filename for a BSD style header """
		filename_len = name[3:]
		return int(filename_len)

	def read_next_header(self):
		"""
		Reads a single new header, returning a its representation, or None at the end of file
		"""
		header = self._read_file_header(self.next_header_offset)
		if header is not None:
			self.headers.append(header)
			if header.type in (HEADER_BSD, HEADER_NORMAL, HEADER_GNU):
				self.archived_files[header.name] = ArchiveFileData(self, header)

		return header

	def __next__(self):
		while True:
			header = self.read_next_header()
			if header is None:
				raise StopIteration
			if header.type in (HEADER_BSD, HEADER_NORMAL, HEADER_GNU):
				return self.archived_files[header.name]
	next = __next__

	def __iter__(self):
		return self

	def read_all_headers(self):
		""" Reads all headers """
		while self.read_next_header() is not None:
			pass

	def close(self):
		""" Closes the archive file descriptor """
		self.file.close()


class AIXBigArchive(Archive):
	"""
	Combines several files into one.

	This is the default ar library archive format for the AIX operating system.

	This file format accommodates both 32-bit and 64-bit object files within
	the same archive.

	"""

	def __init__(self, filename=None, fileobj=None):
		self.headers = []
		self.file = fileobj or open(filename, "rb")
		self._detect_seekable()

		self.position = 0
		self.archived_files = {}

		self.global_header = AIXBigGlobalHeader(
			self._read(AIXBigGlobalHeader.LENGTH))

		self.next_header_offset = self.global_header.first_member

	def _read_file_header(self, offset):
		"""
		Reads and returns a single new file header.

		Also updates next header pointer when this is call as part of an
		iteration.

		"""
		# We are already at the last member.
		if offset == 0:
			return None

		self._seek(offset)

		header_content = self._read(AIXBigFileHeader.MINIMUM_LENGTH)

		if len(header_content) == 0:
			return None

		file_header = AIXBigFileHeader(header_content, offset)

		content = self._read(file_header.remaining_header_length)
		file_header.updateRemainingHeader(content)

		# If we are in the process of iterating file members,
		# update the next header.
		if offset == self.next_header_offset:

			# If we are last in the list, set to 0.
			if offset == self.global_header.last_member:
				self.next_header_offset = 0
			else:
				self.next_header_offset = file_header.next_member

		return file_header


class AIXBigGlobalHeader(object):
	"""
	Each archive begins with a fixed-length header that contains offsets to
	special archive file members. The fixed-length header also contains the
	magic number, which identifies the archive file.

	The fixed-length header has the following format:

	#define __AR_BIG__
	#define AIAMAGBIG "<bigaf>\n"       /* Magic string */
	#define SAIAMAG 8                /*Length of magic string */
	struct  fl_hdr                   /*Fixed-length header */

	{
	char  fl_magic[SAIAMAG];  /* Archive magic string */
	/* Offset to member table  -> members */
	char  fl_memoff[20];
	/* Offset to global symbol table -> global_symbol */
	char  fl_gstoff[20];
	/* Offset global symbol table for 64-bit objects -> global_symbol_64 */
	char  fl_gst64off[20];
	/* Offset to first archive member -> first_member */
	char  fl_fstmoff[20];
	/* Offset to last archive member -> last_member */
	char  fl_lstmoff[20];
	/* Offset to first mem on free list -> first_free_member */
	char  fl_freeoff[20];
	}

	Archive magic string is already parsed, so header is passed without the
	magic string.

	"""

	LENGTH = 128
	AIAMAGBIG = '<bigaf>\n'
	SAIAMAG = 8

	def __init__(self, content):
		self._content = content
		self._checkValidType()
		header = ()
		try:
			header = struct.unpack("8s 20s 20s 20s 20s 20s 20s", content)
		except struct.error:
			raise ArchiveFormatError("bad format for global header")

		(
		magic,
		self.members,
		self.global_symbol,
		self.global_symbol_64,
		self.first_member,
		self.last_member,
		self.first_free_member,
		) = header
		self.members = int(self.members)
		self.global_symbol = int(self.global_symbol)
		self.global_symbol_64 = int(self.global_symbol_64)
		self.first_member = int(self.first_member)
		self.last_member = int(self.last_member)
		self.first_free_member = int(self.first_free_member)

	def _checkValidType(self):
		"""Raise an error if archive had bad type."""
		if len(self._content) < self.LENGTH:
			raise ArchiveFormatError("file to short for AIX big format")

		if self._content[:8] != AIXBigGlobalHeader.AIAMAGBIG:
			raise ArchiveFormatError("this is not an AIX big format archive")


class AIXBigFileHeader(object):
	"""
	Each archive file member is preceded by a file member header,
	which contains the following information about the file member:

	#define  AIAFMAG  "`\n"          /* Header trailer string*/
	struct   ar_hdr                  /* File member header*/
	{
	/* File member size - decimal -> size */
	char ar_size[20];
	/* Next member offset-decimal -> next_member */
	char ar_nxtmem[20];
	/* Previous member offset-dec -> previous_member */
	char ar_prvmem[20];
	/* File member date-decimal -> timestamp*/
	char ar_date[12];
	/* File member userid-decimal -> uid */
	char ar_uid[12];
	/* File member group id-decimal -> gid */
	char ar_gid[12];
	/* File member mode-octal -> mode */
	char ar_mode[12];
	/* File member name length-dec -> filename_length */
	char ar_namlen[4];
	union
		{
		char ar_name[2];  /* Start of member name */
		char ar_fmag[2];  /* AIAFMAG - string to end */
		};
	_ar_name;                /* Header and member name */
	};

	The member header provides support for member names up to 255 characters
	long. The ar_namlen field contains the length of the member name.
	The character string containing the member name begins at the _ar_name
	field. The AIAFMAG string is cosmetic only.

	Each archive member header begins on an even-byte boundary. The total
	length of a member header is:

	sizeof (struct ar_hdr) + ar_namlen
	The actual data for a file member begins at the first even-byte boundary
	beyond the member header and continues for the number of bytes specified
	by the ar_size field. The ar command inserts null bytes for padding
	where necessary.

	All information in the fixed-length header and archive members is in
	printable ASCII format. Numeric information, with the exception of
	the ar_mode field, is stored as decimal numbers;
	the ar_mode field is stored in octal format. Thus, if the archive file
	contains only printable files, you can print the archive.

	"""
	AIAFMAG = '`\n'

	MINIMUM_LENGTH = 112
	type = HEADER_NORMAL

	def __init__(self, content, offset):
		if len(content) < AIXBigFileHeader.MINIMUM_LENGTH:
			raise ArchiveFormatError('file header too short')

		header = ()
		try:
			header = struct.unpack("20s 20s 20s 12s 12s 12s 12s 4s", content)
		except struct.error:
			raise ArchiveFormatError("bad format for file header")

		(
		self.size,
		self.next_member,
		self.previous_member,
		self.timestamp,
		self.uid,
		self.gid,
		self.mode,
		self.filename_length,
		) = header

		self.size = int(self.size)
		self.next_member = int(self.next_member)
		self.previous_member = int(self.previous_member)
		self.timestamp = int(self.timestamp)
		self.uid = int(self.uid)
		self.gid = int(self.gid)
		self.mode = int(self.mode, 8)
		self.filename_length = int(self.filename_length)
		self._header_offset = offset

	@property
	def remaining_header_length(self):
		"""Length of filename content raw data."""
		# actual_filename + ALIGN_PAD + HEADER_TRAILING_STRING
		return Archive._pad2(self.filename_length + len(self.AIAFMAG))

	@property
	def relative_file_offset(self):
		"""Offset to file content start, relative to header."""
		return self.MINIMUM_LENGTH + self.remaining_header_length

	@property
	def file_offset(self):
		"""Offset to file content start, absolute to file."""
		return self._header_offset + self.relative_file_offset

	def updateRemainingHeader(self, content):
		"""Update header with the variable length content."""
		if len(content) < self.remaining_header_length:
			raise ArchiveFormatError('file header end too short')

		if not content.endswith(self.AIAFMAG):
			raise ArchiveFormatError("bad ending for file header")

		self.name = content[:self.filename_length]
