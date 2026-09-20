#!/usr/bin/env python3

import argparse
import ast
import json
import operator
import re
from pathlib import Path


INTEGER_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.FloorDiv: operator.floordiv,
    ast.LShift: operator.lshift,
    ast.RShift: operator.rshift,
    ast.BitOr: operator.or_,
    ast.BitAnd: operator.and_,
}
UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def evaluate_integer(expression):
    def evaluate(node):
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in INTEGER_OPERATORS:
            return INTEGER_OPERATORS[type(node.op)](
                evaluate(node.left), evaluate(node.right)
            )
        if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPERATORS:
            return UNARY_OPERATORS[type(node.op)](evaluate(node.operand))
        raise ValueError(expression)

    return evaluate(ast.parse(expression, mode="eval"))


def read_integer_defines(path, prefix):
    result = {}
    pattern = re.compile(r"^\s*#define\s+([A-Za-z_]\w*)\s+(.+?)\s*(?://.*)?$")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match is None or not match.group(1).startswith(prefix):
            continue
        try:
            result[match.group(1)] = evaluate_integer(match.group(2))
        except (SyntaxError, TypeError, ValueError, ZeroDivisionError):
            continue
    return result


def datatype_name(datatype):
    node = datatype.get("__ast_node__")
    if node == "PntrDecl":
        return f"{datatype_name(datatype['datatype'])} *"
    if node == "ArrayDecl":
        return (
            f"{datatype_name(datatype['datatype'])}"
            f"[{datatype['const_exp']['val']}]"
        )
    if node in ("StructSpec", "UnionSpec"):
        return f"struct {datatype['name']['val']}"
    return {
        "CharType": "char",
        "IntType": "int",
        "VoidType": "void",
        "FunPtrDecl": "function pointer",
    }.get(node, node or "unknown")


def datatype_size(datatype, symbols):
    node = datatype.get("__ast_node__")
    if node == "ArrayDecl":
        return int(datatype["const_exp"]["val"]) * datatype_size(
            datatype["datatype"], symbols
        )
    if node in ("StructSpec", "UnionSpec"):
        return int(symbols[datatype["name"]["val"]]["size"])
    return 1


def extract_structs(symbols):
    structs = {}
    for name, symbol in symbols.items():
        datatype = symbol.get("datatype", {})
        if (
            datatype.get("__ast_node__") != "StructDecl"
            or not symbol.get("complete")
        ):
            continue

        fields = []
        offset = 0
        for allocation in datatype.get("allocs", []):
            field_datatype = allocation["datatype"]
            field_size = datatype_size(field_datatype, symbols)
            fields.append(
                {
                    "name": allocation["name"]["val"],
                    "offset": offset,
                    "size": field_size,
                    "type": datatype_name(field_datatype),
                }
            )
            offset += field_size

        structs[name] = {"size": int(symbol["size"]), "fields": fields}
    return structs


def extract_globals(symbols):
    result = {}
    for name, symbol in symbols.items():
        if symbol.get("frame_kind") != "global" or "addr" not in symbol:
            continue
        result[name] = {
            "address": int(symbol["addr"]),
            "size": int(symbol.get("size", 1)),
            "section": symbol.get("section") or "data",
            "type": datatype_name(symbol.get("datatype", {})),
        }
    return result


def extract_labels(reti_path):
    labels = {}
    address = 0
    pattern = re.compile(r"^# // Block\('([^']+)'(?:,|\))")
    for line in reti_path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match is not None:
            labels.setdefault(match.group(1), address)
        if line and not line.startswith("#"):
            address += 1
    return labels


def extract_interrupt_vector(path):
    source = path.read_text(encoding="utf-8")
    match = re.search(
        r"interrupt_vector_table\s*\[[^]]+\]\s*\([^)]*\)\s*=\s*\{([^}]+)\}",
        source,
        re.DOTALL,
    )
    if match is None:
        match = re.search(
            r"interrupt_vector_table\s*\[[^]]+\][^=]*=\s*\{([^}]+)\}",
            source,
            re.DOTALL,
        )
    if match is None:
        raise ValueError("interrupt_vector_table initializer not found")
    return re.findall(r"\b[A-Za-z_]\w*\b", match.group(1))


def extract_syscall_arguments(path, syscall_names):
    source = path.read_text(encoding="utf-8")
    branches = re.split(
        r"(?:if|else\s+if)\s*\(syscall_number\s*==\s*(SYSCALL_[A-Z0-9_]+)\s*\)",
        source,
    )
    result = {}
    for index in range(1, len(branches), 2):
        name = branches[index]
        body = branches[index + 1]
        if name not in syscall_names:
            continue
        struct_match = re.search(r"\(struct\s+(\w+)\s*\*\)argument", body)
        if struct_match is not None:
            result[name] = {"kind": "struct", "type": struct_match.group(1)}
        elif re.search(r"\(char\s*\*\)argument", body):
            result[name] = {"kind": "string"}
        elif re.search(r"\(struct\s+wait_queue\s*\*\)argument", body):
            result[name] = {"kind": "struct", "type": "wait_queue"}
        elif re.search(r"\bargument\b", body) is None:
            result[name] = {"kind": "none"}
        else:
            result[name] = {"kind": "value"}
    return result


def build_layout(args):
    symbols = json.loads(args.symbol_table.read_text(encoding="utf-8"))["global"]
    syscall_constants = read_integer_defines(args.syscall_header, "SYSCALL_")
    process_states = read_integer_defines(args.process_header, "PROCESS_STATE_")
    memory_constants = read_integer_defines(args.memory_header, "")
    syscall_names = {
        name: value
        for name, value in syscall_constants.items()
        if value >= 0 and name != "SYSCALL_LOAD_PROCESS_CONTINUE"
    }

    return {
        "format_version": 1,
        "system": "PicoOS",
        "globals": extract_globals(symbols),
        "structs": extract_structs(symbols),
        "labels": extract_labels(args.reti),
        "interrupt_vector": extract_interrupt_vector(args.isr_source),
        "syscalls": {
            str(value): {
                "name": name,
                **extract_syscall_arguments(args.syscall_source, syscall_names).get(
                    name, {"kind": "value"}
                ),
            }
            for name, value in syscall_names.items()
        },
        "process_states": {
            str(value): name.removeprefix("PROCESS_STATE_")
            for name, value in process_states.items()
        },
        "memory_constants": memory_constants,
    }


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol-table", type=Path, required=True)
    parser.add_argument("--reti", type=Path, required=True)
    parser.add_argument("--isr-source", type=Path, required=True)
    parser.add_argument("--syscall-source", type=Path, required=True)
    parser.add_argument("--syscall-header", type=Path, required=True)
    parser.add_argument("--process-header", type=Path, required=True)
    parser.add_argument("--memory-header", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    layout = build_layout(args)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(layout, handle, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    main()
