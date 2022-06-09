import arpy
import unittest
import os

# Test thin archive support
class Thin(unittest.TestCase):
    thin_file_name = b'CMakeFiles/ext_lib_normal.dir/ext_lib.c.o'
    thin_ar_name = 'thin.ar'

    def get_file_content(self):
        with open(os.path.dirname(__file__)+'/CMakeFiles/ext_lib_normal.dir/ext_lib.c.o','rb') as f:
            return f.read()

    def test_list(self):
        ar = arpy.Archive(os.path.join(os.path.dirname(__file__), self.thin_ar_name))
        ar.read_all_headers()
        self.assertEqual([self.thin_file_name],
                list(ar.archived_files.keys()))
        self.assertEqual(3, len(ar.headers)) # Symbols, GNUtable, archive
        ar.close()

    def test_content(self):
        ar = arpy.Archive(os.path.join(os.path.dirname(__file__), self.thin_ar_name))
        ar.read_all_headers()
        arpy_entry = ar.archived_files[self.thin_file_name]
        real_content = self.get_file_content()
        arpy_content = arpy_entry.read()
        self.assertEqual(arpy_content, real_content)
        self.assertEqual(arpy_entry.header.size, len(real_content))
        ar.close()

    def test_content_offset_preserving(self):
        ar = arpy.Archive(os.path.join(os.path.dirname(__file__), self.thin_ar_name))
        ar.read_all_headers()
        arpy_entry = ar.archived_files[self.thin_file_name]
        real_content = self.get_file_content()
        arpy_content = arpy_entry.read(10)
        arpy_content += arpy_entry.read(20)
        arpy_content += arpy_entry.read()
        self.assertEqual(arpy_content, real_content)
        self.assertEqual(arpy_entry.header.size, len(real_content))
        ar.close()

if __name__ == "__main__":
	unittest.main()
