import arpy
import unittest
import os

# Test thin archive support
class Thin(unittest.TestCase):
    def test_list(self):
        ar = arpy.Archive(os.path.join(os.path.dirname(__file__), 'thin.ar'))
        ar.read_all_headers()
        self.assertEqual([b'CMakeFiles/ext_lib_normal.dir/ext_lib.c.o'],
                list(ar.archived_files.keys()))
        self.assertEqual(3, len(ar.headers)) # Symbols, GNUtable, archive
        ar.close()

    def test_content(self):
        ar = arpy.Archive(os.path.join(os.path.dirname(__file__), 'thin.ar'))
        ar.read_all_headers()
        arpy_entry = ar.archived_files[b'CMakeFiles/ext_lib_normal.dir/ext_lib.c.o']
        with open(os.path.dirname(__file__)+'/CMakeFiles/ext_lib_normal.dir/ext_lib.c.o','rb') as f:
            real_content = f.read()
        arpy_content = arpy_entry.read()
        self.assertEqual(arpy_content, real_content)
        self.assertEqual(arpy_entry.header.size, len(real_content))
        ar.close()

    def test_content_offset_preserving(self):
        ar = arpy.Archive(os.path.join(os.path.dirname(__file__), 'thin.ar'))
        ar.read_all_headers()
        arpy_entry = ar.archived_files[b'CMakeFiles/ext_lib_normal.dir/ext_lib.c.o']
        with open(os.path.dirname(__file__)+'/CMakeFiles/ext_lib_normal.dir/ext_lib.c.o','rb') as f:
            real_content = f.read()
        arpy_content = arpy_entry.read(10)
        arpy_content += arpy_entry.read(20)
        arpy_content += arpy_entry.read()
        self.assertEqual(arpy_content, real_content)
        self.assertEqual(arpy_entry.header.size, len(real_content))
        ar.close()
