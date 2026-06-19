picoc_compiler ./interrupt_service_routines/isrs.picoc ./kernel/kernel.picoc ./kernel/interrupt_controller.picoc -O1 -i -w -s -o ./kernel.reti
reti_emulator -a kernel.reti
hexyl kernel.bin
cp kernel.sections eprom_startprogram/startprogram.sections
