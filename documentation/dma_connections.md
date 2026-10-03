# FPGA DMA connections

The [intended physical hardware](../README.md#intended-physical-hardware)
implements the DMA controller, UART receive word buffer, interrupt paths, and
SRAM arbitration as FPGA logic. These functions use the existing SRAM and
USB-to-UART connections without requiring an additional external component.

The DMA connections match the implemented PicoOS interface:

| Connection | Required behavior |
| --- | --- |
| CPU to DMA | Memory-mapped registers 12 through 16 expose DMA availability, UART source address, SRAM destination, word count, and status/control. |
| UART receive buffer to DMA | Four serial bytes form one 32-bit word and a ready handshake permits one transfer step. The supported source is the UART receive address. |
| DMA to SRAM arbiter | DMA presents a sequential SRAM write address, 32-bit data, and a request. The arbiter grants either the CPU or DMA access because the asynchronous SRAM has one shared interface. |
| DMA to interrupt controller | Completion or error raises the custom/DMA interrupt request. PicoOS maps it to interrupt service routine-table entry 4 with priority 1. |
| UART to interrupt controller | Receive-ready raises the UART interrupt request. PicoOS maps it to interrupt service routine-table entry 2 with priority 2. |
