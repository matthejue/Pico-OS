# C/PicoC interrupt service routines

`isrs.picoc` contains two interrupt entries and reserves vector slot `3` for
the RETI emulator:

- `0`: send the byte in `ACC` as an ASCII character
- `1`: receive one ASCII byte into `ACC`
- `2`: unused null pointer
- `3`: reserved null pointer for the emulator

The next available project interrupt vector slot is `2`.

The RETI hubs save and restore `DS`, switch `DS` to the periphery address
space (`1048576 * 1024`), perform the UART register handshake, and return with
`RTI`. There is no datatype byte and no integer/string framing; higher-level
code such as `lib/stdio` is responsible for translating integers and strings
to or from ASCII bytes.
