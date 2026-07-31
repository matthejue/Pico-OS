#!/usr/bin/env python3
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path


COMPILER = "picoc_compiler"
DEPENDENCIES_RE = re.compile(r"^\s*//\s*dependencies\s*:\s*(.*?)\s*$")
METADATA_RE = re.compile(
    r"^\s*//\s*(input|in|expected|exp|datasegment|data)\s*:\s*(.*)$"
)
OPTIONS_WITH_VALUE = {
    "-I",
    "--include",
    "-M",
    "--max-depth",
    "-o",
    "--output_name",
    "-C",
    "--startup-source",
    "-k",
    "--kernelheader",
}


def normalized(path):
    return os.path.normpath(path)


def artifact_path(source):
    return str(Path(source).with_suffix(".reti_blocks"))


def source_path(artifact):
    return str(Path(artifact).with_suffix(".picoc"))


def resolve_dependency(source, dependency):
    source_dir = Path(source).parent
    candidates = [Path(dependency)]
    if not Path(dependency).is_absolute():
        candidates.append(source_dir / dependency)

    for candidate in candidates:
        candidate_source = (
            Path(source_path(candidate))
            if candidate.suffix in {".reti_blocks", ".st"}
            else candidate
        )
        if candidate_source.is_file():
            return normalized(str(candidate_source))
    raise FileNotFoundError(f"Dependency source not found for {dependency}")


def dependencies_for(source):
    dependencies = []
    in_block_comment = False
    with open(source, encoding="utf-8") as source_file:
        for line in source_file:
            stripped = line.strip()
            if in_block_comment:
                if "*/" in stripped:
                    in_block_comment = False
                continue
            if not stripped:
                continue
            if stripped.startswith("/*"):
                in_block_comment = "*/" not in stripped
                continue

            match = DEPENDENCIES_RE.match(line)
            if match:
                dependencies.extend(
                    resolve_dependency(source, dependency)
                    for dependency in shlex.split(match.group(1))
                )
                continue
            if stripped.startswith("//"):
                continue
            break
    return dependencies


def dependency_order(roots):
    ordered = []
    visited = set()
    visiting = set()

    def visit(source):
        key = str(Path(source).resolve())
        if key in visited:
            return
        if key in visiting:
            raise ValueError(f"Dependency cycle involving {source}")
        visiting.add(key)
        for dependency in dependencies_for(source):
            visit(dependency)
        visiting.remove(key)
        visited.add(key)
        ordered.append(source)

    for root in roots:
        visit(root)
    return ordered


def parse_arguments(arguments):
    compiler_args = []
    inputs = []
    output = "a.reti"
    startup = None
    kernelheader = None
    compile_only = False
    index = 0

    while index < len(arguments):
        argument = arguments[index]
        if argument in OPTIONS_WITH_VALUE:
            if index + 1 == len(arguments):
                raise ValueError(f"Missing value for {argument}")
            value = arguments[index + 1]
            if argument in {"-o", "--output_name"}:
                output = value
            elif argument in {"-C", "--startup-source"}:
                startup = value
            elif argument in {"-k", "--kernelheader"}:
                kernelheader = value
            else:
                compiler_args.extend((argument, value))
            index += 2
            continue
        if argument in {"-c", "--compile"}:
            compile_only = True
        elif Path(argument).suffix in {".picoc", ".reti_blocks", ".st"}:
            inputs.append(argument)
        else:
            compiler_args.append(argument)
        index += 1

    return compiler_args, inputs, output, startup, kernelheader, compile_only


def run_compiler(arguments):
    return subprocess.run([COMPILER, *arguments]).returncode


def prepend_metadata(source, output):
    metadata = []
    names = {
        "input": "input",
        "in": "input",
        "expected": "expected",
        "exp": "expected",
        "datasegment": "datasegment",
        "data": "datasegment",
    }
    with open(source, encoding="utf-8") as source_file:
        for line in source_file:
            match = METADATA_RE.match(line)
            if match:
                metadata.append(f"# {names[match.group(1)]}:{match.group(2)}\n")
    if not metadata:
        return

    output_path = Path(output)
    contents = output_path.read_text(encoding="utf-8")
    output_path.write_text("".join(metadata) + contents, encoding="utf-8")


def append_unique(paths, path):
    key = str(Path(path).resolve())
    if any(str(Path(existing).resolve()) == key for existing in paths):
        return
    paths.append(path)


def main():
    try:
        (
            compiler_args,
            inputs,
            output,
            startup,
            kernelheader,
            compile_only,
        ) = parse_arguments(sys.argv[1:])

        explicit_sources = [path for path in inputs if Path(path).suffix == ".picoc"]
        roots = list(explicit_sources)
        if startup and Path(startup).suffix == ".picoc":
            roots.append(startup)

        sources = dependency_order(roots)
        for source in sources:
            status = run_compiler([*compiler_args, "-c", source])
            if status != 0:
                return status
        if compile_only:
            return 0

        link_inputs = []
        for path in inputs:
            suffix = Path(path).suffix
            if suffix == ".picoc":
                path = artifact_path(path)
            elif suffix == ".st":
                continue
            append_unique(link_inputs, path)
        for source in sources:
            if source != startup:
                append_unique(link_inputs, artifact_path(source))

        link_args = [*compiler_args, *link_inputs]
        if startup:
            startup_block = (
                artifact_path(startup)
                if Path(startup).suffix == ".picoc"
                else startup
            )
            link_args.extend(("-C", startup_block))
        if kernelheader:
            link_args.extend(("-k", kernelheader))
        link_args.extend(("-o", output))

        status = run_compiler(link_args)
        metadata_requested = any(
            option in compiler_args for option in ("-m", "--metadata_comments")
        )
        if status == 0 and metadata_requested and explicit_sources and not kernelheader:
            prepend_metadata(explicit_sources[0], output)
        return status
    except (FileNotFoundError, OSError, ValueError) as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
