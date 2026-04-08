#!/usr/bin/env python

import os


def main():
    source_dir = os.curdir
    output_dir = os.path.join(source_dir, "converted_to_c")
    os.makedirs(output_dir, exist_ok=True)

    for filename in os.listdir(source_dir):
        if not (filename.endswith(".picoc") or filename.endswith(".h")):
            continue

        src_path = os.path.join(source_dir, filename)
        dest_name = remove_ext(filename) + ".c" if filename.endswith(".picoc") else filename
        dest_path = os.path.join(output_dir, dest_name)

        with open(src_path, "r", encoding="utf-8") as src_file:
            content = src_file.read()

        converted = content.replace("print(", 'printf(" %d", ')
        converted = converted.replace("debug;", "")

        if "input()" in converted:
            input_path = os.path.join(source_dir, remove_ext(filename) + ".input")
            if not os.path.exists(input_path):
                raise FileNotFoundError(
                    f"Missing input file for {filename}: {input_path}"
                )
            with open(input_path, "r", encoding="utf-8") as input_file:
                inputs = input_file.read().replace("\n", "").split(" ")
            while inputs:
                converted = converted.replace("input()", inputs.pop(0), 1)

        if filename.endswith(".picoc"):
            converted_lines = converted.split("\n")
            converted_lines.insert(2, "#include<stdio.h>")
            converted = "\n".join(converted_lines) + "\n"

        with open(dest_path, "w", encoding="utf-8") as dest_file:
            dest_file.write(converted)


def remove_ext(fname):
    """stips of the file extension
    :fname: filename
    :returns: basename of the file

    """
    # if there's no '.' rindex raises a exception, rfind returns -1
    index_of_extension_start = fname.rfind(".")
    if index_of_extension_start == -1:
        return fname
    return fname[0:index_of_extension_start]


if __name__ == "__main__":
    main()
