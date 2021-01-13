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
f = ar.archived_files[b'filename']

and read through:
f.read([length])

random access through seek and tell functions is supported on the archived files.

zipfile-like interface is also available:

ar.namelist() will return a list of names (with possible duplicates)
ar.infolist() will return a list of headers

Use ar.open(name / header) to get the specific file.

You can also use context manager syntax with either the ar file or its contents.
"""

import io
import struct
import os.path
from typing import Optional, List, Dict, BinaryIO, cast, Union


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

	def __init__(self, header: bytes, offset: int):
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
				if uid.strip():
					self.uid = cast(Optional[int], int(uid))
				else:
					self.uid = None
				if gid.strip():
					self.gid = cast(Optional[int], int(gid))
				else:
					self.gid = None
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
			self.file_offset = cast(Optional[int], offset + HEADER_LEN)
		else:
			self.name = None
			self.proxy_name = name
			self.file_offset = None

	def __repr__(self) -> str:
		""" Creates a human-readable summary of a header """
		return '''<ArchiveFileHeader: "%s" type:%s size:%i>''' % (self.name,
				HEADER_TYPES[self.type], self.size)

class ArchiveFileData(io.IOBase):
	""" File-like object used for reading an archived file """

	def __init__(self, ar_obj: "Archive", header: ArchiveFileHeader):
		"""
		Creates a new proxy for the archived file, reusing the archive's file descriptor
		"""
		self.header = header
		self.arobj = ar_obj
		self.last_offset = 0

	def read(self, size: Optional[int] = None) -> bytes:
		""" Reads the data from the archived file, simulates file.read """
		if size is None:
			size = self.header.size

		if self.header.size < self.last_offset + size:
			size = self.header.size - self.last_offset

		self.arobj._seek(cast(int, self.header.file_offset) + self.last_offset)
		data = self.arobj._read(size)
		if len(data) < size:
			raise ArchiveAccessError("incorrect archive file")

		self.last_offset += size
		return data

	def tell(self) -> int:
		""" Returns the position in archived file, simulates file.tell """
		return self.last_offset

	def seek(self, offset: int, whence: int = 0) -> int:
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

		return offset

	def seekable(self) -> bool:
		return self.arobj.seekable

	def __enter__(self):
		return self

	def __exit__(self, _exc_type, _exc_value, _traceback):
		return False

class ArchiveFileDataThin(ArchiveFileData):
	""" File-like object used for reading a thin archived file """

	def __init__(self, ar_obj: "Archive", header: ArchiveFileHeader):
				ArchiveFileData.__init__(self, ar_obj, header)
				self.file_path=os.path.dirname(ar_obj.file.name)+ "/"+header.name.decode()


	def read(self, size: Optional[int] = None) -> bytes:
		""" Reads the data from the archived file, simulates file.read """
		if size is None:
			size = self.header.size - self.last_offset

		with open(self.file_path, "rb") as f:
			f.seek(self.last_offset)
			data=f.read(size)

		if len(data) < size:
			raise ArchiveAccessError("incorrect archive file")
		self.last_offset += size
		return data

class Archive(object):
	""" Archive object allowing reading of *.ar files """

	def __init__(self, filename: Optional[str] = None, fileobj: Optional[BinaryIO] = None):
		self.headers = cast(List[ArchiveFileHeader], [])
		if fileobj:
			self.file = fileobj
		elif filename:
			self.file = open(filename, "rb")
		else:
			raise ValueError("either filename or fileobj argument needs to be given")
		self.position = 0
		self.reached_eof = False
		self._detect_seekable()
		global_header=self._read(GLOBAL_HEADER_LEN)
		if global_header == b"!<arch>\n":
			self.file_data_class = ArchiveFileData
		elif global_header == b"!<thin>\n":
			self.file_data_class = ArchiveFileDataThin
		else:
			raise ArchiveFormatError("file is missing the global header")

		self.next_header_offset = GLOBAL_HEADER_LEN
		self.gnu_table = cast(Dict[int,bytes], {})
		self.archived_files = cast(Dict[bytes,ArchiveFileData], {})

	def _detect_seekable(self) -> None:
		if hasattr(self.file, 'seekable'):
			self.seekable = self.file.seekable()
		else:
			try:
				# .tell() will raise an exception as well
				self.file.tell()
				self.seekable = True
			except Exception:
				self.seekable = False

	def _read(self, length: int) -> bytes:
		data = self.file.read(length)
		self.position += len(data)
		return data

	def _seek(self, offset: int) -> None:
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
					self.reached_eof = True
					return

	def __read_file_header(self, offset: int) -> Optional[ArchiveFileHeader]:
		""" Reads and returns a single new file header """
		self._seek(offset)

		header = self._read(HEADER_LEN)

		if len(header) == 0:
			self.reached_eof = True
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
			self.next_header_offset = Archive.__pad2(new_offset)

		return file_header

	def __read_gnu_table(self, size: int) -> None:
		""" Reads the table of filenames specific to GNU ar format """
		table_string = self._read(size)
		if len(table_string) != size:
			raise ArchiveFormatError("file too short to fit the names table")

		self.gnu_table = {}

		position = 0
		for filename in table_string.split(b"\n"):
			self.gnu_table[position] = filename[:-1] # remove trailing '/'
			position += len(filename) + 1

	def __fix_name(self, header: ArchiveFileHeader) -> int:
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
	def __pad2(num: int) -> int:
		""" Returns a 2-aligned offset """
		if num % 2 == 0:
			return num
		else:
			return num+1

	@staticmethod
	def __get_bsd_filename_len(name: bytes) -> int:
		""" Returns the length of the filename for a BSD style header """
		filename_len = name[3:]
		return int(filename_len)

	def read_next_header(self) -> Optional[ArchiveFileHeader]:
		"""
		Reads a single new header, returning a its representation, or None at the end of file
		"""
		header = self.__read_file_header(self.next_header_offset)
		if header is not None:
			self.headers.append(header)
			if header.type in (HEADER_BSD, HEADER_NORMAL, HEADER_GNU):
				self.archived_files[header.name] = self.file_data_class(self, header)

		return header

	def __next__(self) -> ArchiveFileData:
		while True:
			header = self.read_next_header()
			if header is None:
				raise StopIteration
			if header.type in (HEADER_BSD, HEADER_NORMAL, HEADER_GNU):
				return self.archived_files[header.name]
	next = __next__

	def __iter__(self) -> "Archive":
		return self

	def read_all_headers(self) -> None:
		""" Reads all headers """
		if self.reached_eof:
			return

		while self.read_next_header() is not None:
			pass

	def close(self) -> None:
		""" Closes the archive file descriptor """
		self.file.close()

	### implement a zipfile-like interface as well

	def namelist(self) -> List[bytes]:
		"""
		Return the names of files stored in the archive

		If there are multiple files of the same name, there may be duplicates in the list.
		"""
		self.read_all_headers()
		return [header.name for header in self.headers if header.type in (HEADER_BSD, HEADER_NORMAL, HEADER_GNU)]

	def infolist(self) -> List[ArchiveFileHeader]:
		"""
		Return the headers of files stored in the archive

		These can be used with .open() to get the contents.
		"""
		self.read_all_headers()
		return [header for header in self.headers if header.type in (HEADER_BSD, HEADER_NORMAL, HEADER_GNU)]

	def open(self, name: Union[bytes,ArchiveFileHeader]) -> ArchiveFileData:
		"""
		Return a file-like object based on the provided name or header

		The name can be either a filename, or a header obtained from .read_next_header() or .infolist()
		"""
		self.read_all_headers()

		if isinstance(name, bytes):
			ar_file = self.archived_files.get(name)
			if ar_file is None:
				raise KeyError("There is no item named %r in the archive" % (name,))

			return ar_file

		if isinstance(name, ArchiveFileHeader):
			if name not in self.headers:
				raise KeyError("Provided header does not match this archive")

			return ArchiveFileData(ar_obj=self, header=name)

		raise ValueError("Can't look up file using type %s, expected bytes or ArchiveFileHeader" % (type(name),))

	def __enter__(self):
		return self

	def __exit__(self, _exc_type, _exc_value, _traceback):
		self.close()
		return False
