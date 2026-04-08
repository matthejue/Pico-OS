# Interrupt Service Routine Builder

This directory can be assembled into a single `isrs.reti` file from multiple numbered ISR files.

## Usage

Run the builder in the directory that contains the ISR files:

```bash
python3 build_isrs.py
```

This reads all files matching the supported naming scheme and writes `isrs.reti` in the current directory.

You can also choose a different input directory or output file:

```bash
python3 build_isrs.py --directory path/to/isrs --output path/to/isrs.reti
```

## Supported ISR File Names

Each ISR must live in its own file and use one of these names:

```text
NNN_<name_of_isr>.reti
NNN_<name_of_isr>_<KEYPRESS|INTTIMER>_<priority>.reti
```

Rules:

- `NNN` is a three-digit interrupt index such as `000`, `001`, `002`.
- `<name_of_isr>` is a descriptive name made of letters, numbers, and underscores.
- `_<KEYPRESS|INTTIMER>_<priority>` is optional.
- If the optional suffix is present, the device must be exactly `KEYPRESS` or `INTTIMER`.
- If the optional suffix is present, `<priority>` must be an integer.
- The numbered indices must be consecutive after sorting, for example `000`, `001`, `002`, `003`.

Examples:

```text
000_print_integer_over_uart.reti
001_print_string_over_uart.reti
002_get_user_input_over_uart.reti
003_switch_to_keypress_interrupt_KEYPRESS_1.reti
004_switch_to_scheduler_INTTIMER_2.reti
```

## Translation To `isrs.reti`

The generated `isrs.reti` file has two parts:

1. One `IVTE` line per ISR file at the top.
2. The concatenated ISR bodies below the table entries, in numeric filename order.

The syntax of each generated vector table line is:

```text
IVTE <absolute address of isr starting from 0> [<device> <priority>]
```

How the address is computed:

- Addressing starts at line `0`.
- The `IVTE` table itself occupies the first `N` lines, where `N` is the number of ISR files.
- The first ISR therefore starts at absolute address `N`.
- Each later ISR starts immediately after the previous ISR body ends.
- The script counts addresses by line count in the generated file.

Mapping examples:

```text
000_print_integer_over_uart.reti
001_switch_to_scheduler_INTTIMER_2.reti
```

becomes:

```text
IVTE 2
IVTE <2 + number_of_lines_in_000_print_integer_over_uart.reti> INTTIMER 2
...contents of 000_print_integer_over_uart.reti...
...contents of 001_switch_to_scheduler_INTTIMER_2.reti...
```

Notes:

- The ISR body is copied exactly as it appears in each `.reti` file.
- The ISR name is only used for the filename and is not emitted into `isrs.reti`.
- Files that do not match the supported naming scheme are ignored.
