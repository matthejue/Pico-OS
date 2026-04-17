int printf(char *format, ...);
int scanf(char *format, int *value);

int frame_base() {
    asm("MOVE BAF ACC");
    return 0;
}

int uart_print_integer(int value) {
    asm("LOADIN BAF ACC -2");
    asm("INT 0");
    return 0;
}

int uart_print_string(char *value) {
    asm("LOADIN BAF ACC -2");
    asm("INT 1");
    return 0;
}

int uart_read_word() {
    asm("INT 2");
    return 0;
}

int uart_print_character(int value) {
    char character[2];

    character[0] = value;
    character[1] = 0;
    uart_print_string(character);
    return 0;
}

int append_character(char *buffer, int index, int value) {
    buffer[index] = value;
    return index + 1;
}

int append_string(char *buffer, int index, char *value) {
    int string_index = 0;

    while (value[string_index] != 0) {
        buffer[index] = value[string_index];
        index = index + 1;
        string_index = string_index + 1;
    }

    return index;
}

int append_decimal(char *buffer, int index, int value) {
    char digits[12];
    int digit_count = 0;
    int current = value;

    if (current == 0) {
        buffer[index] = '0';
        return index + 1;
    }

    if (current < 0) {
        buffer[index] = '-';
        index = index + 1;
        current = 0 - current;
    }

    while (current != 0) {
        digits[digit_count] = (current % 10) + '0';
        current = current / 10;
        digit_count = digit_count + 1;
    }

    while (digit_count != 0) {
        digit_count = digit_count - 1;
        buffer[index] = digits[digit_count];
        index = index + 1;
    }

    return index;
}

int input_character_at(int packed, int index) {
    if (index == 0) {
        return packed / 16777216;
    }

    if (index == 1) {
        return (packed / 65536) & 255;
    }

    if (index == 2) {
        return (packed / 256) & 255;
    }

    return packed & 255;
}

int is_decimal_digit(int value) {
    if (value < '0') {
        return 0;
    }

    if (value > '9') {
        return 0;
    }

    return 1;
}

int parse_decimal_input(int packed, int *value) {
    int index = 0;
    int current = input_character_at(packed, 0);
    int sign = 1;
    int has_digit = 0;
    int decimal_digit;
    if (current == '-') {
        sign = -1;
        index = 1;
    }

    while (index < 4) {
        current = input_character_at(packed, index);
        decimal_digit = is_decimal_digit(current);

        if (decimal_digit == 0) {
            index = 4;
        } else {
            *value = (*value * 10) + (current - '0');
            has_digit = 1;
            index = index + 1;
        }
    }

    if (has_digit == 0) {
        return 0;
    }

    *value = (*value) * sign;
    return 1;
}

int next_printf_argument(int argument_index) {
    int *base = (int *)frame_base();
    int slot = argument_index + 2;
    debug;
    return *(base - slot);
}

int printf(char *format, ...) {
    char buffer[256];
    int index = 0;
    int buffer_index = 0;
    int current;
    int argument_index = 0;
    int argument_value;

    while (format[index] != 0) {
        current = format[index];

        if (current == '%') {
            index = index + 1;
            current = format[index];

            if (current == 'd') {
                argument_value = next_printf_argument(argument_index);
                buffer_index = append_decimal(buffer, buffer_index, argument_value);
                argument_index = argument_index + 1;
            } else {
                if (current == 'c') {
                    argument_value = next_printf_argument(argument_index);
                    buffer_index = append_character(buffer, buffer_index, argument_value);
                    argument_index = argument_index + 1;
                } else {
                    if (current == '%') {
                        buffer_index = append_character(buffer, buffer_index, '%');
                    }
                }
            }
        } else {
            buffer_index = append_character(buffer, buffer_index, current);
        }

        index = index + 1;
    }

    buffer[buffer_index] = 0;
    uart_print_string(buffer);
    return 0;
}

int scanf(char *format, int *value) {
    if (format[0] != '%') {
        return 0;
    }

    if (format[2] != 0) {
        return 0;
    }

    int current = format[1];
    int packed = uart_read_word();

    if (current == 'c') {
        *value = input_character_at(packed, 0);
        return 1;
    }

    if (current == 'd') {
        *value = 0;
        return parse_decimal_input(packed, value);
    }

    return 0;
}
