# Development Guidelines

---

## ChatGPT Script Generation

When ChatGPT generates shell commands intended to create or update project files, the generated scripts shall favor non-interactive, reproducible mechanisms.

Preferred techniques are:

- printf with output redirection (`>` or `>>`);
- Python scripts writing files through pathlib;
- other deterministic, non-interactive file generation methods.

Interactive editors and long here-documents should be avoided whenever possible because they are more likely to cause formatting issues, terminal synchronization problems or copy/paste corruption.

The objective is that every generated command can be copied into the terminal and executed without requiring manual editing.
