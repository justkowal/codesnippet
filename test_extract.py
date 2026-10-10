#!/usr/bin/env python3
"""
test_extract.py - Test suite for extract.py symbol extractor.
"""

import subprocess
import unittest
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXTRACT_PY = os.path.join(SCRIPT_DIR, "extract.py")
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
MATRIX_HPP = os.path.join(REPO_ROOT, "Project01", "include", "Matrix.hpp")
MATRIX_CPP = os.path.join(REPO_ROOT, "Project01", "src", "Matrix.cpp")
ACTIVITY1_CPP = os.path.join(REPO_ROOT, "Project01", "src", "activity1.cpp")
PLOT_PY = os.path.join(REPO_ROOT, "Project01", "scripts", "plot_activity3.py")


def run_extractor(*args):
    cmd = [sys.executable, EXTRACT_PY] + list(args)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


class TestExtract(unittest.TestCase):

    def test_cpp_class_extraction(self):
        code, out, _ = run_extractor(MATRIX_HPP, "Matrix")
        self.assertEqual(code, 0)
        self.assertIn("class Matrix", out)
        self.assertIn("size_t leading_dimension() const;", out)

    def test_cpp_constructor_header(self):
        code, out, _ = run_extractor(MATRIX_HPP, "Matrix::Matrix")
        self.assertEqual(code, 0)
        self.assertIn("template <typename Function>", out)
        self.assertIn("Matrix(size_t n, size_t m, Function f)", out)

    def test_cpp_constructor_index(self):
        code, out, _ = run_extractor(MATRIX_CPP, "Matrix::Matrix[0]")
        self.assertEqual(code, 0)
        self.assertIn("Row-major LDA must be at least the number of columns", out)
        self.assertNotIn("Matrix(size_t n, size_t m, double initialValue)", out)

    def test_cpp_method_source(self):
        code, out, _ = run_extractor(MATRIX_CPP, "Matrix::rows")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "size_t Matrix::rows() const\n{\n    return n;\n}")

    def test_cpp_method_header_declaration(self):
        code, out, _ = run_extractor(MATRIX_HPP, "Matrix::rows")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "size_t rows() const;")

    def test_cpp_operator(self):
        code, out, _ = run_extractor(MATRIX_CPP, "Matrix::operator()")
        self.assertEqual(code, 0)
        self.assertIn("double &Matrix::operator()(size_t i, size_t j)", out)

    def test_cpp_main_function(self):
        code, out, _ = run_extractor(ACTIVITY1_CPP, "main")
        self.assertEqual(code, 0)
        self.assertIn("int main()", out)
        self.assertIn("return 0;", out)

    def test_python_function(self):
        code, out, _ = run_extractor(PLOT_PY, "read_norms")
        self.assertEqual(code, 0)
        self.assertIn("def read_norms(path: pathlib.Path):", out)
        self.assertIn("return k, y", out)

    def test_line_range(self):
        code, out, _ = run_extractor(MATRIX_HPP, "25-36")
        self.assertEqual(code, 0)
        self.assertIn("template <typename Function>", out)
        self.assertIn("row_offset(i, j, lda)", out)

    def test_symbol_not_found(self):
        code, out, err = run_extractor(MATRIX_HPP, "NonExistentSymbol")
        self.assertEqual(code, 0)
        self.assertIn("Symbol 'NonExistentSymbol' not found", out)

    def test_missing_file(self):
        code, out, err = run_extractor("does_not_exist.cpp", "foo")
        self.assertEqual(code, 0)
        self.assertIn("File not found", out)

    def test_meta_out(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w+", delete=False) as tf:
            meta_path = tf.name
        try:
            code, out, err = run_extractor(MATRIX_CPP, "Matrix::rows", "--meta-out", meta_path)
            self.assertEqual(code, 0)
            with open(meta_path, "r") as f:
                content = f.read()
            self.assertIn("\\gdef\\csnip@meta@startline{19}", content)
            self.assertIn("\\gdef\\csnip@meta@endline{22}", content)
            self.assertIn("\\gdef\\csnip@meta@lines{19-22}", content)
        finally:
            if os.path.exists(meta_path):
                os.remove(meta_path)


if __name__ == "__main__":
    unittest.main()

