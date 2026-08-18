# Filesystem Functions Explanation

#### You:
Please explain all functions in the uploaded files to me in detail. But don't make it too long.

#### ChatGPT:
I’ll read both files, identify every function and its role, then explain the control flow and important edge cases without going line by line unnecessarily.

These two files implement the **filesystem-facing operations on PicoOS file descriptors**, especially `open()`, `read()`, `write()`, and `seek()`. Actual regular files live on the host machine and are accessed through the UART protocol.

### Overall structure

The public interface in `filesystem(6).header` exposes:

```c
int open_file_descriptor(struct OpenRequest *request);
int read_file_descriptor(struct IoRequest *request, int *caller_context);
int write_file_descriptor(struct IoRequest *request);
int seek_file_descriptor(struct SeekRequest *request);
```

The `.picoc` file also contains several helper functions used internally.

## 1. `receive_file_size()`

```c
int receive_file_size(char *path)
```

Asks the host filesystem for the size of a file.

Conceptually:

```text
PicoOS                     Host
  |                         |
  | FILE_SIZE(path) ------> |
  | <---------- size        |
```

It first sends:

```c
    uart_send_host_request("file-size ", path);
```

and then receives a complete integer using:

```c
receive_word();
```

The returned value appears to be:

- `>= 0`, file size
- `-1`, file does not exist or an error occurred

---

## 2. `file_exists()`

```c
bool file_exists(char *path)
```

Checks whether a host file exists.

It simply uses:

```c
int size = receive_file_size(path);
```

and considers:

```c
size == -1
```

to mean "does not exist".

So even an empty file is correctly considered existing because its size is `0`.

---

## 3. Direct UART output selection

The filesystem sends host requests directly with `uart_send_host_request()`.
This tells the host that subsequent UART output should be redirected somewhere else.

For example:

```c
uart_send_host_request("write ", "stderr");
```

or:

```c
uart_send_host_request("append ", descriptor->path);
```

This is important because the same UART connection is apparently used for both terminal output and file output.

To restore UART output to standard output, the filesystem sends:

```c
uart_send_host_request("write ", "stdout");
```

Thus code such as:

```c
uart_send_host_request("append ", descriptor->path);
write_uart_bytes(...);
uart_send_host_request("write ", "stdout");
```

means:

```text
redirect UART -> file
send characters
redirect UART -> stdout
```

---

# File descriptor allocation

## 5. `free_file_descriptor()`

```c
int free_file_descriptor(struct FileDescriptorTable *table)
```

Finds the first unused file descriptor in a process's descriptor table.

It starts with:

```c
int index = 3;
```

because descriptors `0`, `1`, and `2` are conventionally reserved:

```text
0 = stdin
1 = stdout
2 = stderr
3+ = regular files
```

It looks for:

```c
table->entries[index].kind == FILE_DESCRIPTOR_FREE
```

and returns that descriptor number.

If the table is full:

```c
return -1;
```

---

# Opening files

## 6. `open_file_descriptor()`

```c
int open_file_descriptor(struct OpenRequest *request)
```

This is the main implementation behind opening a file.

### Step 1: get the current process's descriptor table

```c
struct FileDescriptorTable *table =
    current_process()->file_descriptors;
```

Every process therefore has its own file descriptor table.

### Step 2: validate the request

It rejects:

```c
request == NULL
request->path == NULL
```

It then extracts just the access mode:

```c
access_mode = request->flags & O_ACCMODE;
```

and permits:

```c
O_RDONLY
O_WRONLY
O_RDWR
```

Anything else returns `-1`.

### Step 3: allocate an FD

```c
file_descriptor = free_file_descriptor(table);
```

For example:

```text
0 stdin
1 stdout
2 stderr
3 FREE
4 FREE
```

would produce:

```text
fd = 3
```

### Step 4: construct the absolute path

```c
build_process_path(
    request->path,
    absolute_path,
    PATH_MAX
)
```

This is presumably where a relative path such as:

```text
foo.txt
```

is combined with the current process's working directory.

Then:

```c
path = copy_file_path(absolute_path);
```

creates a separately allocated persistent copy of that path.

This is necessary because:

```c
char absolute_path[512];
```

is only a local stack array and disappears when the function returns.

### Step 5: handle `O_TRUNC`

```c
if ((request->flags & O_TRUNC) != 0)
```

A read-only file cannot be truncated:

```c
if (access_mode == O_RDONLY)
    return -1;
```

Otherwise:

```c
uart_send_host_request("write ", path);
uart_send_host_request("write ", "stdout");
```

The `"write "` command apparently creates or truncates the host file.

No data has to be written. Merely selecting it using `"write "` causes the truncation.

### Step 6: handle nonexistent files

If there is no `O_TRUNC`, it tests:

```c
!file_exists(path)
```

If the file does not exist and `O_CREAT` was **not** supplied:

```c
return -1;
```

With `O_CREAT`, it creates the file using the same `"write "` command.

### Step 7: initialize the descriptor

```c
descriptor->kind = FILE_DESCRIPTOR_FILE;
descriptor->flags = request->flags;
descriptor->offset = 0;
descriptor->path = path;
```

The resulting descriptor therefore remembers:

- that this is a regular file
- its open flags
- the current logical file position
- its absolute path

Finally it returns the descriptor number.

For example:

```c
open("hello.txt", O_RDONLY)
```

might return:

```text
3
```

---

# Reading

## 7. `read_regular_file()`

```c
int read_regular_file(
    struct FileDescriptor *descriptor,
    char *buffer,
    int count,
    bool show_loading_bar
)
```

Performs the actual read of a regular host file.

It tells the host:

```c
uart_send_file_range_command(
    descriptor->path,
    descriptor->offset,
    count
);
```

So the request effectively means:

```text
read at most `count` bytes
starting at `descriptor->offset`
from this path
```

The host first responds with:

```c
byte_count = receive_word();
```

This tells PicoOS how many bytes are actually coming.

For example, requesting:

```text
offset = 100
count  = 50
```

might yield only:

```text
byte_count = 12
```

if only 12 bytes remain before EOF.

Then it receives those bytes individually:

```c
while (copied < byte_count) {
    value = receive_byte_over_uart();
    buffer[copied] = value;
    copied++;
}
```

There is also optional loading-bar handling.

Finally:

```c
descriptor->offset += copied;
```

So a successful 20-byte read advances the file position by 20.

The return value is the actual number of bytes read.

---

## 8. `read_file_descriptor()`

```c
int read_file_descriptor(
    struct IoRequest *request,
    int *caller_context
)
```

This is the generic `read()` dispatcher.

It first validates:

- request is non-NULL
- `count >= 0`
- buffer exists when `count > 0`
- file descriptor number is valid

A zero-length read:

```c
count == 0
```

immediately returns `0`.

It then verifies that the FD is readable:

```c
file_descriptor_can_read(descriptor)
```

This likely checks flags such as:

```text
O_RDONLY -> yes
O_RDWR   -> yes
O_WRONLY -> no
```

### stdin

For:

```c
descriptor->kind == FILE_DESCRIPTOR_STDIN
```

it delegates to:

```c
begin_stdin_read(...)
```

The `caller_context` argument is relevant here because stdin reading can apparently block and therefore interact with process/syscall context handling.

### regular file

For:

```c
FILE_DESCRIPTOR_FILE
```

it calls:

```c
read_regular_file(...)
```

Anything else returns `-1`.

So the structure is essentially:

```text
read(fd)
   |
   +-- stdin ------> begin_stdin_read()
   |
   +-- file -------> read_regular_file()
   |
   +-- unsupported -> error
```

---

# Writing

## 9. `write_uart_bytes()`

```c
void write_uart_bytes(char *buffer, int count)
```

A very small helper that sends the buffer byte by byte:

```c
while (index < count) {
    uart_print_character(buffer[index]);
    index++;
}
```

The destination depends on what UART output was previously selected.

That means the same function can write to:

```text
stdout
stderr
host file
```

---

## 10. `write_file_descriptor()`

```c
int write_file_descriptor(struct IoRequest *request)
```

This is the generic implementation of `write()`.

It performs the same basic request validation as `read_file_descriptor()`.

Then:

```c
file_descriptor_can_write(descriptor)
```

ensures that writing is permitted.

### stderr

For:

```c
FILE_DESCRIPTOR_STDERR
```

it redirects UART output:

```c
        uart_send_host_request("write ", "stderr");
```

### regular file

For:

```c
FILE_DESCRIPTOR_FILE
```

it uses:

```c
        uart_send_host_request("append ", descriptor->path);
```

Then all bytes are sent:

```c
write_uart_bytes(request->buffer, request->count);
```

After non-stdout output, UART is restored:

```c
        uart_send_host_request("write ", "stdout");
```

Finally:

```c
descriptor->offset += request->count;
```

and the number of written bytes is returned.

### Important detail

Regular-file writes use:

```c
"append "
```

rather than the descriptor's current offset.

Therefore, judging from this file alone, **writes always go to the end of the host file**. The stored `descriptor->offset` is incremented, but it is not supplied to the host when writing.

Consequently, a `seek()` changes where subsequent **reads** happen, but apparently does not reposition subsequent writes.

That differs from normal POSIX `write()` semantics and is worth keeping in mind.

---

# Seeking

## 11. `seek_file_descriptor()`

```c
int seek_file_descriptor(struct SeekRequest *request)
```

Changes the descriptor's logical offset, analogous to `lseek()`.

It only permits:

```c
FILE_DESCRIPTOR_FILE
```

so you cannot seek on stdin, stdout, or stderr.

There are three origins.

### `SEEK_SET`

```c
offset = request->offset;
```

Sets an absolute position.

Example:

```text
SEEK_SET, 20
```

means:

```text
position = 20
```

### `SEEK_CUR`

```c
offset = descriptor->offset + request->offset;
```

Moves relative to the current position.

Example:

```text
current = 100
offset  = -20

new position = 80
```

### `SEEK_END`

First retrieves the file size:

```c
offset = receive_file_size(descriptor->path);
```

Then adds the requested displacement:

```c
offset += request->offset;
```

For a 1000-byte file:

```text
SEEK_END, -100
```

produces:

```text
offset = 900
```

Negative resulting offsets are rejected:

```c
if (offset < 0)
    return -1;
```

Otherwise:

```c
descriptor->offset = offset;
```

and the new offset is returned.

Seeking beyond EOF is allowed because there is no upper-bound check.

---

# How the pieces fit together

The central design is:

```text
Process
  |
  v
FileDescriptorTable
  |
  +-- 0 stdin
  +-- 1 stdout
  +-- 2 stderr
  +-- 3 regular file
  +-- 4 regular file
       |
       +-- flags
       +-- path
       +-- offset
```

Regular files are not actually stored or manipulated directly by the PicoOS kernel. PicoOS sends commands over UART to the host:

```text
PicoOS kernel
     |
     | UART commands
     v
Host filesystem implementation
     |
     v
Linux/Windows/macOS file
```

So this file mainly provides the **file-descriptor abstraction and POSIX-like semantics**, while `host_filesystem` and the UART protocol provide the actual connection to the host filesystem.

The four most important entry points are therefore:

```text
open_file_descriptor()   -> allocate FD and open/create/truncate path
read_file_descriptor()   -> dispatch stdin or regular-file reading
write_file_descriptor()  -> dispatch stdout/stderr/file writing
seek_file_descriptor()   -> manipulate regular-file read offset
```

One especially important implementation detail is that **reads use `descriptor->offset`, while regular-file writes currently use `"append "` and therefore appear not to honor that offset**.
