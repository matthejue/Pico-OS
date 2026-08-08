# Binary Loading Protocol

PicoOS executable binaries begin with five big-endian 32-bit metadata words:

1. `codesegment_start`
2. `datasegment_start`
3. `heap_start`
4. `heap_size`
5. `stack_start`

The RETI emulator copies these fields from the compiler-generated `.sections`
file into the binary before the encoded program words. The surrounding UART
file protocol prefixes the complete binary with its word count, so loaders
subtract five before copying the executable payload into SRAM.

The compiler writes `heap_size: -1` and `stack_start: -1` by default. A user can
edit the generated `.sections` file before assembling to select explicit
process values. PicoOS resolves process `heap_size: -1` to 1000 cells, and a
process with `stack_start: -1` receives 1000 stack cells above its effective
heap.

The kernel loader receives and discards the binary `heap_start` and `heap_size`
words. Kernel allocation uses `KERNEL_HEAP_START` and `KERNEL_HEAP_SIZE` from
the compiler-generated `kernel/memory_constants.header`; the generated heap
size is 4096 cells. The bootloader retains its existing end-of-SRAM kernel
stack default when binary `stack_start` is `-1`.
