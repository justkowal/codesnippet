# codesnippet - Dynamic Code Snippet Extractor for LaTeX

`codesnippet` is a LaTeX package that dynamically extracts symbols (classes, functions, methods, constructors, operator overloads, and line ranges) from C++, C, Python, and other source code files and embeds them into your document with syntax highlighting via `minted`.

It provides a lightweight, modern visual design: delicate rules, muted line numbering, clean header titles above code blocks, project root path resolution, scoped environments, and flexible reference modes (semantic path, real file location with line numbers, or both).

---

## Package Features

- **AST & Structural Extraction**: Python AST and robust boundary-matching for C++ classes, constructors, methods, operator overloads, templates, and functions.
- **Project Root & Scoped Environments**: Set a global or environment-level project root (`root=..`), so snippet paths never need clumsy `../` prefixes and are resolved relative to the compilation directory.
- **Reference by Semantic Path, Real Location, or Both**: Refer to snippets in headers or prose by their symbol name (`Matrix::Matrix`), real source location (`include/Matrix.hpp:19-36`), or both (`Matrix::Matrix \hfill include/Matrix.hpp:19-36`).
- **In-Text Cross-Referencing**: Add `label=mykey` to snippets and refer to them anywhere in your document using `\snippetref{mykey}`, `\snippetloc{mykey}`, `\snippetlines{mykey}`, and `\snippetfile{mykey}`.
- **Refined, Lightweight Styling**: Subtle 0.5pt rules, muted line numbers aligned within text margins, and clean titles placed cleanly above code frames (no heavy border cuts).
- **Document-Wide & Per-Snippet Customization**: Full control via `\codesnippetsetup{...}` and per-snippet optional arguments `\codesnippet[...]{...}{...}` with automatic `minted` option pass-through.

---

## Project Structure

```
codesnippet/
├── codesnippet.sty   # The LaTeX package
├── extract.py        # Python AST & structural symbol extractor
├── test_extract.py   # Test suite for extract.py
└── README.md         # Package documentation
```

---

## Quick Start

### 1. In Your LaTeX Document

```latex
\documentclass[11pt,a4paper]{article}
\usepackage[margin=0.75in]{geometry}
\usepackage{codesnippet}

% Global document configuration
\codesnippetsetup{
    root        = ..,              % Project root relative to compilation pwd
    ref         = both,            % Show both semantic name & real location
    refformat   = inline,          % Title flush-left, location flush-right
    theme       = colorful,        % Pygments theme
    fontsize    = \small,
    framerule   = 0.5pt,
    rulecolor   = gray!75,
}

\begin{document}

\section{Implementation Details}

% 1. Uses root=.. so path is written without ../
%    Displays: Matrix Dynamic Constructor    include/Matrix.hpp:19-36
\codesnippet[
    title = {Matrix Dynamic Constructor},
    highlightlines = {8-12},
    label = snip:ctor
]{include/Matrix.hpp}{Matrix::Matrix}

% 2. Refer to snippet by real location only:
\codesnippet[ref=location, linenos=false]{src/Matrix.cpp}{Matrix::rows}

% 3. Scoped Project Environment (overrides root & formatting locally)
\begin{codesnippetproject}[ref=both, refformat=bracket]{..}
\codesnippet[label=snip:blas]{src/Matrix.cpp}{Matrix::multiply_blas}
\end{codesnippetproject}

\section{Cross-Referencing in Prose}
As defined in snippet \snippetref{snip:ctor}, located at \snippetloc{snip:ctor} (lines \snippetlines{snip:ctor}).

\end{document}
```

### 2. Compile with Shell Escape

```bash
pdflatex -shell-escape report.tex
```

---

## Project Root & Path Resolution

Paths to source files can be resolved relative to a project root rather than repeating relative path jumps (e.g. `../`):

1. **Global Root**: Set globally via `\usepackage[root=..]{codesnippet}` or `\codesnippetsetup{root=..}`.
2. **Scoped Environment**: Use `\begin{codesnippetproject}{<root>} ... \end{codesnippetproject}` (or shorthand `\begin{snippetproject}{<root>}`). Paths inside the environment are resolved relative to `<root>`. When the environment ends, the root reverts to the outer scope.
3. **Per-Snippet Root**: Pass `root=<path>` directly to `\codesnippet[root=..]{...}{...}`.
4. **Default (No Root Set)**: If no root is specified, paths are resolved relative to the LaTeX compilation directory (`pwd`). Absolute paths (starting with `/`) are always used directly.

---

## Snippet Reference Modes (`ref` & `refformat`)

You can control how snippets are referred to in their header blocks:

| Mode (`ref=`) | Description | Example Display |
|---|---|---|
| `semantic` *(default)* | Shows the symbol name or user-defined `title` | `Matrix::Matrix` |
| `location` (or `real`) | Shows the file path relative to root and extracted line range | `include/Matrix.hpp:19-36` |
| `both` | Shows both semantic name and real file location | `Matrix::Matrix` with `include/Matrix.hpp:19-36` |

When `ref=both` is selected, `refformat` controls the presentation:

| Format (`refformat=`) | Description | Example |
|---|---|---|
| `inline` *(default)* | Semantic title flush-left, real location flush-right | `Matrix::Matrix` \hfill `include/Matrix.hpp:19-36` |
| `bracket` | Location in brackets following title | `Matrix::Matrix [include/Matrix.hpp:19-36]` |
| `stacked` | Title on line 1, location on line 2 | `Matrix::Matrix` <br> `include/Matrix.hpp:19-36` |

---

## Cross-Referencing in Document Prose

Attach a label using `\codesnippet[label=mykey]{file}{symbol}`. You can then reference it anywhere in your document text:

- `\snippetref{mykey}`: Expands to the semantic title (e.g. `Matrix::multiply_blas`).
- `\snippetloc{mykey}`: Expands to the real location (e.g. `src/Matrix.cpp:138-163`).
- `\snippetlines{mykey}`: Expands to the extracted line range (e.g. `138-163`).
- `\snippetfile{mykey}`: Expands to the file path relative to root (e.g. `src/Matrix.cpp`).
- Standard `\ref{mykey}`: Standard LaTeX reference.

---

## Configuration Options

Settings can be specified globally in `\codesnippetsetup{...}` or locally on any snippet via `\codesnippet[...]`.

### Root & References

| Option | Default | Description |
|---|---|---|
| `root` | *(empty)* | Project root path relative to compilation pwd (or absolute). |
| `ref` / `titlemode` | `semantic` | Reference mode: `semantic`, `location` (or `real`), or `both`. |
| `refformat` | `inline` | Layout for `ref=both`: `inline`, `bracket`, or `stacked`. |
| `lineprefix` | `:` | Delimiter before line numbers (e.g. `:` or `, lines `). |
| `locprefix` | *(empty)* | Prefix string before location in stacked format (e.g. `Source:~`). |
| `locstyle` / `refstyle` | `\footnotesize\ttfamily` | Font style command for real location text. |
| `loccolor` / `refcolor` | `gray!45!black` | Color expression for real location text. |

### Title & Header Styling

| Option | Default | Description |
|---|---|---|
| `title` | Symbol name | Custom snippet title text. Use `title=none` to suppress the title. |
| `showtitle` | `true` | Toggle title display (`true` or `false`). |
| `titleprefix` | *(empty)* | Optional prefix before title (e.g. `Snippet:~` or `Listing:~`). |
| `titlestyle` | `\footnotesize\ttfamily\bfseries` | Font command for title text. |
| `titlecolor` | `gray!25!black` | Color expression for snippet title. |
| `titlesep` | `0.2em` | Vertical spacing between header and code frame. |

### Bounds & Framing

| Option | Default | Description |
|---|---|---|
| `frame` | `lines` | Border type: `lines`, `single`, `leftline`, `topline`, `bottomline`, or `none`. |
| `framerule` | `0.5pt` | Border line thickness. |
| `rulecolor` | `gray!75` | Border line color expression (e.g. `black!25`, `gray!70`, `blue!40`). |
| `framesep` | `2.5mm` | Inner padding between frame rules and code text. |
| `bgcolor` | *(none)* | Background fill color (e.g. `gray!5`, `black!3`). |

### Line Numbers & Margins

| Option | Default | Description |
|---|---|---|
| `linenos` | `true` | Show line numbers (`true` or `false`). |
| `numbercolor` | `gray!55` | Color expression for line numbers. |
| `numbersep` | `8pt` | Horizontal gap between line numbers and code text. |
| `firstnumber` | `1` | Starting line number (`auto`, `1`, `last`, or integer). |
| `stepnumber` | `1` | Interval for line numbering (e.g. `1`, `5`). |
| `xleftmargin` | `1.8em` | Left indentation keeping line numbers within the text body. |
| `xrightmargin` | `0pt` | Right margin indentation. |

### Syntax & Interpreter

| Option | Default | Description |
|---|---|---|
| `theme` / `style` | `colorful` | Pygments syntax highlighting theme (e.g. `colorful`, `tango`, `friendly`, `vs`, `github-light`). |
| `lang` | `cpp` | Default programming language lexer for `minted`. |
| `python` | `python3` | Command or path for the Python interpreter. |
| `script` | `extract.py` | Path to extractor script (auto-detects current directory or `texmf`). |
| `fontsize` | `\small` | Font size command (e.g. `\small`, `\footnotesize`, `\scriptsize`). |
| `breaklines` | `true` | Automatically wrap long lines (`true` or `false`). |
| `tabsize` | `4` | Tab stop width in spaces. |
| `highlightlines` | *(none)* | Line numbers to highlight, e.g. `{1, 3-5}`. |
| `highlightcolor` | *(minted default)* | Background color for highlighted lines. |

---

## Supported Symbol Queries

| Query Format | Example | Description |
|---|---|---|
| Method / Constructor | `Matrix::Matrix` | Extracts constructor definitions |
| Specific Overload | `Matrix::Matrix[0]` or `Matrix::Matrix[1]` | Extracts a specific overload by 0-based index |
| Signature Filter | `Matrix::Matrix[Function]` | Extracts the overload containing `Function` |
| Member Method | `Matrix::rows` | Extracts out-of-line definition or header declaration |
| Operator Overload | `Matrix::operator()` or `Vector::operator*` | Extracts overloaded operators |
| Class / Struct | `Matrix` | Extracts the entire `class Matrix { ... };` block |
| Free Function | `main` or `activity1` | Extracts standalone functions |
| Python Function / Class | `read_norms` or `MyClass.method` | Extracts Python functions, decorators, or classes via AST |
| Explicit Line Range | `25-36` or `L25-L36` | Extracts lines 25 to 36 inclusive |

---

## Installation (`TEXMFHOME`)

To make `\usepackage{codesnippet}` available globally to all LaTeX projects:

```bash
mkdir -p $(kpsewhich -var-value TEXMFHOME)/tex/latex/codesnippet
cp codesnippet.sty extract.py $(kpsewhich -var-value TEXMFHOME)/tex/latex/codesnippet/
chmod +x $(kpsewhich -var-value TEXMFHOME)/tex/latex/codesnippet/extract.py
texhash
```
