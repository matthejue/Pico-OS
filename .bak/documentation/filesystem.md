# Explain File Functions

#### You:
Please explain the functions in those files to me in detail. But don't make it too long.

#### ChatGPT:
I’ll go through the header and implementation together, group helper functions with the public filesystem operations, and focus on what each function does, its key parameters, and how it fits into the overall filesystem flow.

These two files implement the main **file-descriptor-level filesystem operations** of PicoOS: opening, reading, writing, and seeking. The actual files live on the host computer, so PicoOS communicates with the host filesystem over UART.

A useful mental model is:

```text
User program
    |
    | open/read/write/lseek syscall
    v
filesystem.picoc
    |
    +--> terminal handling, for terminal descriptors
    |
    +--> UART commands, for normal files
              |
              v
        Host filesystem
```

## `receive_file_size`

```c
int receive_file_size(char *path)
```

Asks the host computer for the size of a file.

It sends:

```c
uart_send_host_request("file-size ", path);
```

and then receives one integer:

```c
return receive_word();
```

So conceptually:

```text
PicoOS:  "file-size /some/file"
Host:    1234
```

A negative result, specifically `-1` here, means that the file does not exist or the operation failed.

---

## `file_exists`

```c
bool file_exists(char *path)
```

A small helper that determines whether a file exists.

It simply calls:

```c
int size = receive_file_size(path);
```

and interprets `-1` as nonexistent:

```c
if (size == -1)
    return false;
```

So even an empty file with size `0` correctly counts as existing.

---

## `free_file_descriptor`

```c
int free_file_descriptor(struct FileDescriptorTable *table)
```

Searches the current process's file descriptor table for an unused slot.

It walks through:

```c
table->entries[0]
table->entries[1]
...
```

until it finds:

```c
kind == FILE_DESCRIPTOR_FREE
```

It returns the index of that entry, which becomes the new file descriptor number.

For example:

```text
fd 0   stdin
fd 1   stdout
fd 2   stderr
fd 3   FREE      <- returns 3
fd 4   FREE
```

If every slot is occupied, it returns `-1`.

---

# `open_file_descriptor`

```c
int open_file_descriptor(struct OpenRequest *request)
```

This is the main implementation of `open()`.

It performs several steps.

### 1. Validate the access mode

```c
access_mode = request->flags & O_ACCMODE;
```

This extracts:

```text
O_RDONLY
O_WRONLY
O_RDWR
```

Anything else is rejected.

### 2. Find a free descriptor

```c
file_descriptor = free_file_descriptor(table);
```

If no descriptor is available, opening fails.

### 3. Convert the path into an absolute process path

```c
build_process_path(request->path, absolute_path, PATH_MAX)
```

So something like:

```text
notes/a.txt
```

might become something like:

```text
/home/.../notes/a.txt
```

depending on the process's current directory.

Then:

```c
path = copy_file_path(absolute_path);
```

allocates persistent storage for that path. This is necessary because the descriptor must remember the filename after `open_file_descriptor()` returns.

### 4. Handle creation and truncation

Terminal device paths are treated specially and skip normal host-file handling.

For a normal file, `O_TRUNC` causes:

```c
uart_send_host_request("write ", path);
uart_send_host_request("write ", "stdout");
```

which effectively opens/truncates the host file.

Importantly:

```c
O_RDONLY | O_TRUNC
```

is rejected because truncating modifies the file.

If the file does not exist:

```c
!file_exists(path)
```

then opening only succeeds if:

```c
O_CREAT
```

was supplied.

### 5. Initialize the descriptor

```c
descriptor->kind = FILE_DESCRIPTOR_FILE;
descriptor->flags = request->flags;
descriptor->offset = 0;
descriptor->path = path;
```

So every opened file remembers:

```text
kind
flags
current offset
path
```

The returned value is the descriptor index, for example `3`.

---

# `read_regular_file`

```c
int read_regular_file(
    struct FileDescriptor *descriptor,
    struct IoRequest *request
)
```

This performs one bounded chunk of a **normal host file** read. The public
`read()` wrapper may call it through syscall 16 several times, returning to
userspace between incomplete chunks. It does not invoke scheduler yield: a
timer that expires in the non-preemptive kernel is deferred to the syscall
return boundary.

First PicoOS tells the host:

```c
uart_send_file_range_command(
    descriptor->path,
    descriptor->offset,
    requested
);
```

`requested` is the smaller of the unread part of `request->count` and the
1 KiB host-transfer limit. Every chunk is a complete `read-range` transaction,
so another process can safely send a host request after the syscall returns.

Conceptually:

```text
Give me up to 100 bytes
from file X
starting at byte 50.
```

The host answers with the number of bytes it will actually send:

```c
byte_count = receive_word();
```

This may be smaller than `requested`, for example when reaching EOF.

Then the bytes arrive one by one:

```c
value = receive_byte_over_uart();
request->buffer[request->transferred + copied] = value;
```

There is also optional loading-bar handling for large transfers.

Finally:

```c
descriptor->offset += copied;
```

So if the descriptor was at offset `20` and 8 bytes were read:

```text
before: offset = 20
read:            8 bytes
after:  offset = 28
```

The function stores whether the wrapper has finished in `request->complete`
and returns the number of bytes read by this chunk. Loading-bar progress uses
the cumulative `transferred` count rather than restarting for every chunk.

---

# `read_file_descriptor`

```c
int read_file_descriptor(
    struct IoRequest *request,
    int *caller_context
)
```

This is the higher-level implementation of one `read()` syscall chunk.

It first validates the descriptor:

```c
file_descriptor_is_valid(...)
```

It rejects negative or inconsistent progress values. A request whose total
count has already been transferred is marked complete and returns `0`:

```c
request->count == request->transferred
```

Then it verifies that the descriptor exists and is readable:

```c
descriptor->kind == FILE_DESCRIPTOR_FREE
!file_descriptor_can_read(descriptor)
```

### Terminal descriptor

If the path represents a terminal:

```c
is_terminal_device_path(descriptor->path)
```

it calls:

```c
begin_terminal_read(...)
```

instead of communicating with a normal file.

The `caller_context` is important here because terminal input may have to
**block the process** until keyboard/UART input arrives. Terminal reads set
`request->complete` immediately because their short-read and blocking behavior
must not be turned into a fill-the-entire-buffer loop.

### Normal file

For:

```c
descriptor->kind == FILE_DESCRIPTOR_FILE
```

it calls:

```c
read_regular_file(...)
```

So this function acts mainly as a dispatcher:

```text
read(fd)
   |
   +--> terminal? --> begin_terminal_read()
   |
   +--> file?     --> read_regular_file() --> return to userspace
                                           --> repeat if incomplete
```

---

# `write_uart_bytes`

```c
void write_uart_bytes(char *buffer, int count)
```

A simple helper that transmits the contents of a buffer one byte at a time:

```c
uart_print_character(buffer[index]);
```

Conceptually:

```text
buffer = "Hello"
count = 5

UART -> H
UART -> e
UART -> l
UART -> l
UART -> o
```

It does not itself decide *where* those bytes go. `write_file_descriptor()` first tells the host whether the following bytes belong to a file, stdout, or stderr.

Foreground process selection is not part of this path. A background process
with stdout still pointing to `/device/terminal.dev` can write to the terminal;
foreground ownership is used only for terminal input and terminal-generated
signals.

---

# `write_file_descriptor`

```c
int write_file_descriptor(struct IoRequest *request)
```

This implements `write()`.

First it validates the descriptor and checks that it has write permission:

```c
file_descriptor_can_write(descriptor)
```

Then behavior depends on the descriptor.

### Terminal / stderr

For a terminal path, normal terminal output can simply be transmitted.

For `stderr`, it explicitly tells the host:

```c
uart_send_host_request("write ", "stderr");
```

so subsequent UART characters are treated as stderr output.

### Normal file

The normal starting position is:

```c
write_offset = descriptor->offset;
```

But if:

```c
O_APPEND
```

is set, it deliberately ignores the current offset and asks for the current end of the file:

```c
write_offset = receive_file_size(descriptor->path);
```

Then it tells the host:

```c
uart_send_file_write_command(
    descriptor->path,
    write_offset
);
```

After that:

```c
write_uart_bytes(request->buffer, request->count);
```

sends the actual contents.

Finally, normal routing is restored with:

```c
uart_send_host_request("write ", "stdout");
```

where necessary.

The descriptor offset is updated:

```c
descriptor->offset = write_offset + request->count;
```

This also explains the relationship between `lseek()` and `O_APPEND`:

```text
lseek(fd, 10, SEEK_SET)
        |
        v
descriptor->offset = 10

write(fd, ...)
        |
        +-- without O_APPEND --> write at 10
        |
        +-- with O_APPEND ----> ignore 10,
                                obtain file size,
                                write at EOF
```

So `lseek()` still changes the descriptor's offset, but `O_APPEND` overrides it whenever a write actually happens.

---

# `seek_file_descriptor`

```c
int seek_file_descriptor(struct SeekRequest *request)
```

This implements the equivalent of `lseek()`.

First, it verifies the descriptor.

Seeking is only permitted for ordinary files:

```c
descriptor->kind != FILE_DESCRIPTOR_FILE
```

or terminal paths are rejected.

That makes sense because a terminal is a byte stream, not a random-access file.

Then it handles the three standard origins.

### `SEEK_SET`

```c
offset = request->offset;
```

The requested offset is absolute.

```text
lseek(fd, 20, SEEK_SET)

new offset = 20
```

### `SEEK_CUR`

```c
offset = descriptor->offset + request->offset;
```

Relative to the current position.

```text
current = 20
lseek(fd, 5, SEEK_CUR)

new offset = 25
```

Negative relative offsets work too, provided the final value is not negative:

```text
current = 20
lseek(fd, -5, SEEK_CUR)

new offset = 15
```

### `SEEK_END`

First obtain the current file size:

```c
offset = receive_file_size(descriptor->path);
```

then add the requested offset:

```c
offset += request->offset;
```

For example:

```text
file size = 100

lseek(fd, -10, SEEK_END)

new offset = 90
```

Finally:

```c
if (offset < 0)
    return -1;

descriptor->offset = offset;
return offset;
```

Notice that an offset **past EOF is allowed**. For example:

```c
lseek(fd, 1000, SEEK_SET);
```

can set the position to 1000 even if the file currently contains only 100 bytes. Only negative offsets are forbidden.

---

## `receive_byte_over_uart`

At the top you also have:

```c
int receive_byte_over_uart(void);
```

This is only a **forward declaration**, not an implementation in this file.

`read_regular_file()` uses it to receive individual bytes sent by the host.

---

## How the important functions fit together

The four functions exposed by `filesystem.header` are:

```c
open_file_descriptor(...)
read_file_descriptor(...)
write_file_descriptor(...)
seek_file_descriptor(...)
```

They approximately correspond to the Unix/POSIX operations:

| PicoOS function           | Unix concept |
| ------------------------- | ------------ |
| `open_file_descriptor()`  | `open()`     |
| `read_file_descriptor()`  | `read()`     |
| `write_file_descriptor()` | `write()`    |
| `seek_file_descriptor()`  | `lseek()`    |

The central state is the `FileDescriptor`:

```text
FileDescriptor
├── kind
├── flags
├── offset
└── path
```

The especially important idea is that **PicoOS itself does not contain the ordinary file contents**. The descriptor stores the logical state, such as path, flags, and current offset, while actual file operations are sent over UART to the host filesystem.
