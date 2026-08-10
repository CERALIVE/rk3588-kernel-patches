// SPDX-License-Identifier: GPL-2.0
/*
 * qa-write-errno.c — write to a path and report the RAW errno of write(2).
 *
 * The fault harnesses assert that an operation failed with a particular errno.
 * Done from the shell, the only thing available to assert on is a diagnostic
 * string, and that string is produced by whichever utility happened to perform
 * the write: `printf: write error: Cannot allocate memory` from bash, something
 * else from dash, and something else again under a non-C locale. It never
 * contains the symbol the driver returned.
 *
 * This helper removes the rendering step. On failure it prints the errno NUMBER
 * and nothing else, and exits 1; on success it prints nothing and exits 0. What
 * the harness then asserts is the value the kernel returned.
 *
 * Usage: qa-write-errno <path> <data>
 * Exit:  0 write succeeded  1 write failed (errno on stdout)  2 usage error
 */

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv)
{
	const char *path, *data;
	size_t len;
	ssize_t n;
	int fd;

	if (argc != 3) {
		fprintf(stderr, "usage: %s <path> <data>\n", argv[0]);
		return 2;
	}

	path = argv[1];
	data = argv[2];
	len = strlen(data);

	/*
	 * O_WRONLY, never O_CREAT: a debugfs or sysfs attribute that is missing
	 * must be reported as ENOENT rather than quietly created as a file that
	 * accepts every write, which would turn a missing knob into a pass.
	 */
	fd = open(path, O_WRONLY);
	if (fd < 0) {
		printf("%d\n", errno);
		return 1;
	}

	n = write(fd, data, len);
	if (n < 0) {
		int err = errno;

		close(fd);
		printf("%d\n", err);
		return 1;
	}

	/*
	 * sysfs `bind`/`unbind` and debugfs attributes report a store failure
	 * from close() when the write itself was buffered, so the close is part
	 * of the assertion rather than cleanup.
	 */
	if (close(fd) < 0) {
		printf("%d\n", errno);
		return 1;
	}

	if ((size_t)n != len) {
		printf("%d\n", EIO);
		return 1;
	}

	return 0;
}
