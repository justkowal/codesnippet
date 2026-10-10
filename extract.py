#!/usr/bin/env python3
"""
extract.py - Dynamic Code Snippet Extractor for LaTeX/Minted.

Extracts symbols (functions, methods, classes, constructors, structs) from source files
(C++, C, Python, and other languages) using AST and structural syntax parsing.

Usage:
    python3 extract.py <filepath> <symbol> [options]

Examples:
    python3 extract.py Matrix.hpp Matrix::Matrix
    python3 extract.py Matrix.hpp "Matrix::Matrix[Function]"
    python3 extract.py Matrix.hpp "Matrix::Matrix[1]"
    python3 extract.py src/Matrix.cpp Matrix::rows
    python3 extract.py scripts/plot.py plot_norms
    python3 extract.py Matrix.hpp Matrix
    python3 extract.py Matrix.hpp 25-36
"""

import argparse
import ast
import os
import re
import sys
import textwrap
from typing import List, Optional, Tuple, Dict, Any


def strip_comments_and_strings(code: str) -> str:
    """
    Replaces comments and string literals with spaces while preserving
    exact character positions and line numbers.
    """
    out = []
    n = len(code)
    i = 0
    in_line_comment = False
    in_block_comment = False
    in_string = False
    in_char = False
    in_raw_string = False
    raw_delimiter = ""

    while i < n:
        c = code[i]
        next_c = code[i + 1] if i + 1 < n else ""

        if in_line_comment:
            if c == '\n':
                in_line_comment = False
                out.append('\n')
            else:
                out.append(' ')
            i += 1
        elif in_block_comment:
            if c == '*' and next_c == '/':
                in_block_comment = False
                out.append('  ')
                i += 2
            elif c == '\n':
                out.append('\n')
                i += 1
            else:
                out.append(' ')
                i += 1
        elif in_raw_string:
            match = re.match(r'\)' + re.escape(raw_delimiter) + r'"', code[i:])
            if match:
                span = match.end()
                out.append(' ' * span)
                i += span
                in_raw_string = False
            elif c == '\n':
                out.append('\n')
                i += 1
            else:
                out.append(' ')
                i += 1
        elif in_string:
            if c == '\\':
                out.append('  ')
                i += 2
            elif c == '"':
                in_string = False
                out.append(' ')
                i += 1
            elif c == '\n':
                out.append('\n')
                i += 1
            else:
                out.append(' ')
                i += 1
        elif in_char:
            if c == '\\':
                out.append('  ')
                i += 2
            elif c == "'":
                in_char = False
                out.append(' ')
                i += 1
            elif c == '\n':
                out.append('\n')
                i += 1
            else:
                out.append(' ')
                i += 1
        else:
            if c == '/' and next_c == '/':
                in_line_comment = True
                out.append('  ')
                i += 2
            elif c == '/' and next_c == '*':
                in_block_comment = True
                out.append('  ')
                i += 2
            elif c == 'R' and next_c == '"':
                m = re.match(r'R"([^( \t\r\n\v\f]*)\(', code[i:])
                if m:
                    raw_delimiter = m.group(1)
                    in_raw_string = True
                    span = m.end()
                    out.append(' ' * span)
                    i += span
                else:
                    out.append('R')
                    i += 1
            elif c == '"':
                in_string = True
                out.append(' ')
                i += 1
            elif c == "'":
                in_char = True
                out.append(' ')
                i += 1
            else:
                out.append(c)
                i += 1

    return "".join(out)


def find_matching_delimiter(text: str, start_index: int, open_delim='{', close_delim='}') -> int:
    """Finds the index of the matching close delimiter in text."""
    depth = 0
    n = len(text)
    for i in range(start_index, n):
        if text[i] == open_delim:
            depth += 1
        elif text[i] == close_delim:
            depth -= 1
            if depth == 0:
                return i
    return -1


class SnippetResult:
    def __init__(self, name: str, code: str, start_line: int, end_line: int,
                 is_definition: bool = True, qualname: str = "", signature: str = ""):
        self.name = name
        self.code = code
        self.start_line = start_line
        self.end_line = end_line
        self.is_definition = is_definition
        self.qualname = qualname if qualname else name
        self.signature = signature

    def __repr__(self):
        return f"<SnippetResult {self.qualname} L{self.start_line}-{self.end_line} def={self.is_definition}>"


def extract_python_symbols(source: str, symbol_query: str) -> List[SnippetResult]:
    """Extracts Python classes, methods, or functions using AST."""
    results = []
    lines = source.splitlines()

    try:
        tree = ast.parse(source)
    except Exception:
        return results

    query_parts = symbol_query.replace('::', '.').split('.')
    target_class = query_parts[0] if len(query_parts) > 1 else None
    target_member = query_parts[-1]

    def get_node_lines(node):
        start_line = node.lineno
        if hasattr(node, 'decorator_list') and node.decorator_list:
            start_line = min(d.lineno for d in node.decorator_list)
        end_line = getattr(node, 'end_lineno', node.lineno)
        snippet_lines = lines[start_line - 1 : end_line]
        snippet_text = "\n".join(snippet_lines)
        return start_line, end_line, textwrap.dedent(snippet_text)

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if target_class is None and (node.name == target_member or symbol_query == node.name):
                s, e, text = get_node_lines(node)
                results.append(SnippetResult(node.name, text, s, e, is_definition=True, qualname=node.name))
        elif isinstance(node, ast.ClassDef):
            if target_class is None and (node.name == target_member or symbol_query == node.name):
                s, e, text = get_node_lines(node)
                results.append(SnippetResult(node.name, text, s, e, is_definition=True, qualname=node.name))
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    qual = f"{node.name}.{item.name}"
                    qual_cpp = f"{node.name}::{item.name}"
                    if target_class in (None, node.name) and (item.name == target_member or symbol_query in (qual, qual_cpp)):
                        s, e, text = get_node_lines(item)
                        results.append(SnippetResult(item.name, text, s, e, is_definition=True, qualname=qual_cpp))

    return results


def find_statement_start_line(source: str, sanitized: str, open_pos: int, lines: List[str]) -> int:
    """
    Finds the exact 1-indexed start line of a C/C++ statement or declaration
    leading up to open_pos (which is either an opening '{' or a semicolon ';').
    Stops backwards at statement boundaries (';', '{', '}', access specifiers,
    preprocessor directives).
    """
    pos = open_pos - 1
    boundary_pos = 0

    while pos >= 0:
        ch = sanitized[pos]
        if ch in ';{}':
            boundary_pos = pos + 1
            break
        # Check if line is a preprocessor directive
        if ch == '\n':
            prev_nl = sanitized.rfind('\n', 0, pos)
            line_content = source[prev_nl + 1 : pos].strip()
            if line_content.startswith('#'):
                boundary_pos = pos + 1
                break
        pos -= 1

    # Check for access specifiers (public:, private:, protected:) between boundary_pos and open_pos
    between = sanitized[boundary_pos:open_pos]
    acc_m = list(re.finditer(r'\b(public|private|protected)\s*:', between))
    if acc_m:
        last_acc = acc_m[-1]
        boundary_pos = boundary_pos + last_acc.end()

    # Advance past any whitespace/newlines to find the first character of the statement
    stmt_char = boundary_pos
    while stmt_char < open_pos and source[stmt_char] in ' \t\r\n':
        stmt_char += 1

    # Check if there is an immediately attached doc comment or template above stmt_char
    cur_line = source.count('\n', 0, stmt_char) + 1
    first_line = cur_line
    idx = cur_line - 2
    while idx >= 0:
        l = lines[idx].strip()
        if not l:
            break
        if l.startswith('template') or l.startswith('//') or l.startswith('/*') or l.startswith('*') or l.startswith('*/'):
            first_line = idx + 1
            idx -= 1
        else:
            break

    return first_line


def extract_cpp_symbols(source: str, symbol_query: str) -> List[SnippetResult]:
    """
    Extracts C/C++ classes, structs, functions, methods, constructors, operators
    by analyzing structural tokens and scopes.
    """
    results: List[SnippetResult] = []
    lines = source.splitlines()
    sanitized = strip_comments_and_strings(source)
    n = len(source)

    def get_line_number(char_idx: int) -> int:
        return source.count('\n', 0, char_idx) + 1

    # 1. Find class / struct blocks to build scope maps
    class_regex = re.compile(r'\b(class|struct)\s+([A-Za-z0-9_]+)\b', re.MULTILINE)
    classes = []
    for m in class_regex.finditer(sanitized):
        kind, class_name = m.group(1), m.group(2)
        brace_pos = sanitized.find('{', m.end())
        semi_pos = sanitized.find(';', m.end())
        if semi_pos != -1 and (brace_pos == -1 or semi_pos < brace_pos):
            continue  # forward declaration
        if brace_pos != -1:
            matching_brace = find_matching_delimiter(sanitized, brace_pos, '{', '}')
            if matching_brace != -1:
                end_pos = matching_brace + 1
                after_close = sanitized[end_pos:end_pos+10].lstrip()
                if after_close.startswith(';'):
                    end_pos = sanitized.find(';', end_pos) + 1
                start_l = find_statement_start_line(source, sanitized, m.start(), lines)
                end_l = get_line_number(end_pos)
                classes.append({
                    'name': class_name,
                    'start_idx': m.start(),
                    'brace_start': brace_pos,
                    'brace_end': matching_brace,
                    'end_idx': end_pos,
                    'start_line': start_l,
                    'end_line': end_l
                })

    # Class definitions
    for c in classes:
        snippet_text = "\n".join(lines[c['start_line'] - 1 : c['end_line']])
        results.append(SnippetResult(
            name=c['name'],
            code=textwrap.dedent(snippet_text),
            start_line=c['start_line'],
            end_line=c['end_line'],
            is_definition=True,
            qualname=c['name'],
            signature=f"class {c['name']}"
        ))

    # 2. Find functions / constructors / methods with bodies '{ ... }'
    i = 0
    while i < n:
        if sanitized[i] == '{':
            open_brace = i
            close_brace = find_matching_delimiter(sanitized, open_brace, '{', '}')
            if close_brace == -1:
                i += 1
                continue

            # Skip if this is a class/struct body
            if any(c['brace_start'] == open_brace for c in classes):
                i = open_brace + 1
                continue

            # Get signature between previous statement delimiter and open_brace
            start_l = find_statement_start_line(source, sanitized, open_brace, lines)
            end_l = get_line_number(close_brace)

            raw_sig_lines = lines[start_l - 1 : get_line_number(open_brace)]
            signature = " ".join(l.strip() for l in raw_sig_lines)

            # Skip control-flow blocks: if, for, while, switch, catch, do, namespace, extern
            first_word = re.split(r'\s|\(', signature)[0] if signature else ""
            if first_word in ('namespace', 'if', 'for', 'while', 'switch', 'catch', 'do', 'extern'):
                i = open_brace + 1
                continue

            # Determine enclosing class
            enclosing_class = None
            for c in classes:
                if c['brace_start'] < open_brace < c['brace_end']:
                    enclosing_class = c['name']
                    break

            func_name = None
            qualname = None

            # Pattern for operator overload
            op_match = re.search(r'([A-Za-z0-9_]+::)?(operator\s*[^(\s]+|\boperator\s*\(\s*\)|\boperator\s*\[\s*\])\s*\(', signature)
            if op_match:
                prefix = op_match.group(1) or ""
                op_name = op_match.group(2)
                op_name = re.sub(r'\s+', '', op_name)
                if prefix:
                    prefix_name = prefix.rstrip(':')
                    qualname = f"{prefix_name}::{op_name}"
                    func_name = op_name
                elif enclosing_class:
                    qualname = f"{enclosing_class}::{op_name}"
                    func_name = op_name
                else:
                    qualname = op_name
                    func_name = op_name
            else:
                param_pos = signature.find('(')
                if param_pos != -1:
                    pre_param = signature[:param_pos].strip()
                    id_match = re.search(r'([A-Za-z0-9_]+::)?(~?[A-Za-z0-9_]+)$', pre_param)
                    if id_match:
                        prefix = id_match.group(1) or ""
                        base_id = id_match.group(2)
                        if prefix:
                            prefix_name = prefix.rstrip(':')
                            qualname = f"{prefix_name}::{base_id}"
                            func_name = base_id
                        elif enclosing_class:
                            qualname = f"{enclosing_class}::{base_id}"
                            func_name = base_id
                        else:
                            qualname = base_id
                            func_name = base_id

            if func_name and qualname:
                snippet_text = "\n".join(lines[start_l - 1 : end_l])
                results.append(SnippetResult(
                    name=func_name,
                    code=textwrap.dedent(snippet_text),
                    start_line=start_l,
                    end_line=end_l,
                    is_definition=True,
                    qualname=qualname,
                    signature=signature
                ))

            i = open_brace + 1
        else:
            i += 1

    # 3. In-class declarations ending in ';'
    for c in classes:
        class_content = source[c['brace_start'] + 1 : c['brace_end']]
        sanitized_content = sanitized[c['brace_start'] + 1 : c['brace_end']]

        decl_regex = re.compile(r'([^\;\{\}]+?\b(~?[A-Za-z0-9_]+|operator\s*[^(\s]+|operator\s*\(\s*\)|operator\s*\[\s*\])\s*\([^;]*?\)[^;]*?);', re.MULTILINE)
        for m in decl_regex.finditer(sanitized_content):
            matched_str = class_content[m.start():m.end()]
            raw_decl = matched_str.strip()
            name_token = m.group(2)
            name_token = re.sub(r'\s+', '', name_token)

            first_tok = raw_decl.split()[0] if raw_decl.split() else ""
            if first_tok in ('typedef', 'using'):
                continue

            leading_ws = len(matched_str) - len(matched_str.lstrip())
            decl_start_offset = c['brace_start'] + 1 + m.start() + leading_ws
            decl_end_offset = c['brace_start'] + 1 + m.end()

            start_l = get_line_number(decl_start_offset)
            end_l = get_line_number(decl_end_offset)
            snippet_text = "\n".join(lines[start_l - 1 : end_l])

            qualname = f"{c['name']}::{name_token}"
            results.append(SnippetResult(
                name=name_token,
                code=textwrap.dedent(snippet_text),
                start_line=start_l,
                end_line=end_l,
                is_definition=False,
                qualname=qualname,
                signature=raw_decl
            ))

    return results


def filter_results(candidates: List[SnippetResult], symbol_query: str) -> List[SnippetResult]:
    """Filters results matching query."""
    normalized_query = symbol_query.replace('.', '::').strip()

    # Check for modifier/filter in query e.g. "Matrix::Matrix[Function]" or "Matrix::Matrix[0]"
    filter_arg = None
    m = re.search(r'\[(.*?)\]$', normalized_query)
    if m:
        filter_arg = m.group(1).strip()
        normalized_query = normalized_query[:m.start()].strip()
    else:
        m2 = re.search(r':(\d+)$', normalized_query)
        if m2:
            filter_arg = m2.group(1).strip()
            normalized_query = normalized_query[:m2.start()].strip()

    query_parts = normalized_query.split('::')
    target_class = query_parts[0] if len(query_parts) > 1 else None
    target_member = query_parts[-1]

    matches = []
    for item in candidates:
        matched = False
        clean_item_qual = re.sub(r'\s+', '', item.qualname)
        clean_query = re.sub(r'\s+', '', normalized_query)

        if item.qualname == normalized_query or clean_item_qual == clean_query:
            matched = True
        elif target_class is not None and item.qualname.startswith(f"{target_class}::") and item.name == target_member:
            matched = True
        elif target_class is None and item.name == target_member:
            matched = True

        if matched:
            matches.append(item)

    # Apply filter_arg if present
    if filter_arg is not None and matches:
        if filter_arg.isdigit():
            idx = int(filter_arg)
            if 0 <= idx < len(matches):
                return [matches[idx]]
            return []
        else:
            # Filter by substring in signature or code
            sub_matches = [item for item in matches if filter_arg.lower() in item.signature.lower() or filter_arg.lower() in item.code.lower()]
            if sub_matches:
                return sub_matches

    return matches


def extract_fallback(source: str, symbol_query: str) -> List[SnippetResult]:
    """Fallback extractor using regex or line ranges."""
    lines = source.splitlines()

    # 1. Line range: "25-36" or "L25-L36" or "25:36"
    range_match = re.match(r'^L?(\d+)[:-]L?(\d+)$', symbol_query.strip())
    if range_match:
        s = int(range_match.group(1))
        e = int(range_match.group(2))
        s = max(1, min(s, len(lines)))
        e = max(s, min(e, len(lines)))
        snippet = "\n".join(lines[s - 1 : e])
        return [SnippetResult(symbol_query, textwrap.dedent(snippet), s, e, is_definition=True)]

    # 2. Regex pattern: /pattern/
    if symbol_query.startswith('/') and symbol_query.endswith('/') and len(symbol_query) > 2:
        pat = symbol_query[1:-1]
        regex = re.compile(pat)
        for idx, line in enumerate(lines):
            if regex.search(line):
                return [SnippetResult(symbol_query, line, idx + 1, idx + 1, is_definition=True)]

    # 3. Simple text search fallback: find symbol line and brace block if any
    for idx, line in enumerate(lines):
        if re.search(r'\b' + re.escape(symbol_query) + r'\b', line):
            start_l = idx + 1
            rest = "\n".join(lines[idx:])
            brace_pos = rest.find('{')
            if brace_pos != -1:
                matching = find_matching_delimiter(rest, brace_pos, '{', '}')
                if matching != -1:
                    block_text = rest[:matching + 1]
                    end_l = start_l + block_text.count('\n')
                    return [SnippetResult(symbol_query, textwrap.dedent(block_text), start_l, end_l, is_definition=True)]
            return [SnippetResult(symbol_query, textwrap.dedent(line), start_l, start_l, is_definition=False)]

    return []


def write_meta(meta_path: Optional[str], start_line: int, end_line: int, symbol: str, filepath: str) -> None:
    if not meta_path:
        return
    l_str = f"{start_line}" if start_line == end_line else f"{start_line}-{end_line}"
    try:
        with open(meta_path, "w", encoding="utf-8") as mf:
            mf.write("\\makeatletter\n")
            mf.write(f"\\gdef\\csnip@meta@startline{{{start_line}}}%\n")
            mf.write(f"\\gdef\\csnip@meta@endline{{{end_line}}}%\n")
            mf.write(f"\\gdef\\csnip@meta@lines{{{l_str}}}%\n")
            mf.write("\\makeatother\n")
    except Exception as e:
        sys.stderr.write(f"Warning: could not write meta file: {e}\n")


def main():
    parser = argparse.ArgumentParser(description="Extract code snippets for LaTeX minted inclusion.")
    parser.add_argument("file", help="Path to source file")
    parser.add_argument("symbol", help="Symbol name, qualified name, or line range")
    parser.add_argument("-a", "--all", action="store_true", help="Extract all matching occurrences (including declarations)")
    parser.add_argument("-i", "--index", type=int, default=None, help="Index of match to extract (0-based)")
    parser.add_argument("--strict", action="store_true", help="Exit with non-zero status on error")
    parser.add_argument("--meta-out", default=None, help="Output file for LaTeX metadata")
    args = parser.parse_args()

    norm_file = os.path.normpath(args.file)

    if not os.path.isfile(norm_file):
        write_meta(args.meta_out, 0, 0, args.symbol, norm_file)
        msg = f"// Error: File not found: {args.file}"
        sys.stderr.write(f"{msg}\n")
        print(msg)
        sys.exit(1 if args.strict else 0)

    try:
        with open(norm_file, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
    except Exception as e:
        write_meta(args.meta_out, 0, 0, args.symbol, norm_file)
        msg = f"// Error reading file {norm_file}: {e}"
        sys.stderr.write(f"{msg}\n")
        print(msg)
        sys.exit(1 if args.strict else 0)

    ext = os.path.splitext(norm_file)[1].lower()

    all_symbols: List[SnippetResult] = []
    if ext == ".py":
        all_symbols = extract_python_symbols(source, args.symbol)
    elif ext in (".hpp", ".h", ".cpp", ".cc", ".cxx", ".c", ".hh", ".hxx", ".tpp", ".ipp"):
        all_symbols = extract_cpp_symbols(source, args.symbol)

    results = filter_results(all_symbols, args.symbol)

    # Fallback if no results
    if not results:
        results = extract_fallback(source, args.symbol)

    if not results:
        write_meta(args.meta_out, 0, 0, args.symbol, norm_file)
        msg = f"// Error: Symbol '{args.symbol}' not found in {norm_file}"
        sys.stderr.write(f"{msg}\n")
        print(msg)
        sys.exit(1 if args.strict else 0)

    # Prefer full definitions unless declarations requested via --all
    defs = [r for r in results if r.is_definition]
    if defs and not args.all:
        candidates = defs
    else:
        candidates = results

    # Deduplicate candidate snippets that cover identical lines
    unique_candidates: List[SnippetResult] = []
    seen_ranges = set()
    for c in candidates:
        r_key = (c.start_line, c.end_line)
        if r_key not in seen_ranges:
            seen_ranges.add(r_key)
            unique_candidates.append(c)

    if args.index is not None:
        if 0 <= args.index < len(unique_candidates):
            selected = [unique_candidates[args.index]]
        else:
            write_meta(args.meta_out, 0, 0, args.symbol, norm_file)
            msg = f"// Error: Index {args.index} out of range for '{args.symbol}' (found {len(unique_candidates)} matches)"
            sys.stderr.write(f"{msg}\n")
            print(msg)
            sys.exit(1 if args.strict else 0)
    else:
        selected = unique_candidates

    s_line = min(c.start_line for c in selected) if selected else 0
    e_line = max(c.end_line for c in selected) if selected else 0
    write_meta(args.meta_out, s_line, e_line, args.symbol, norm_file)

    output_snippets = [c.code.strip() for c in selected]
    print("\n\n".join(output_snippets))


if __name__ == "__main__":
    main()

