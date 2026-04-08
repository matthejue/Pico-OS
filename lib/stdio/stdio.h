#ifndef STDIO_H
#define STDIO_H

int printf(char *format, int value);
int scanf(char *format, int *value);

#define printf_s(text) printf("%s", (int)(text))
#define printf_d(number) printf("%d", (number))
#define scanf_d(out) scanf("%d", (out))

#endif
