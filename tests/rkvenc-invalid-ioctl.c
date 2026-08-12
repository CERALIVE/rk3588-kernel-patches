// SPDX-License-Identifier: (GPL-2.0+ OR MIT)
/*
 * rkvenc-invalid-ioctl — drive malformed MPP_IOC_CFG_V1 requests at
 * /dev/mpp_service and assert the exact errno each one must produce.
 *
 * RUNS ON HARDWARE ONLY, against the non-shipping `edge-test` kernel under
 * KASAN. Every case here corresponds to a specific unchecked computation in the
 * request parser: an offset+size that wraps, a size below one dword that makes
 * `offset + size - 4` underflow, an unaligned offset that truncates the dword
 * index, a request that merely OVERLAPS a register class being copied as though
 * it were CONTAINED by it, and a byte/element bound mismatch in the FD
 * translation table.
 *
 * THE RESULT-COPY CASE IS THE SERIOUS ONE. `class-overrun` exercises the path
 * that copies status registers back to userspace. Before the fix that copy was
 * located by the class's START offset only and then ran for the caller's own
 * claimed size, so it read past the end of a kmalloc'd buffer into whatever
 * followed it on the kernel heap and handed the result to userspace. On this
 * kernel KASAN is what turns "wrong answer" into a report; the expected errno
 * below is what turns it into a test.
 *
 * EXPECTATIONS ARE DATA. Every case's expected errno comes from
 * expected-errno.tsv, never from this file, so changing what a malformed
 * request returns is a visible diff in a reviewed table rather than an edit
 * buried in a harness.
 *
 * Output contract: exactly `RESULT=PASS case=<name> ...` on success, non-zero
 * exit otherwise.
 *
 * Copyright (C) 2026 CeraLive
 */

#include <errno.h>
#include <stdarg.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

#include <linux/rkvenc.h>

#define MPP_FLAGS_MULTI_MSG_LOCAL	0x00000001u
#define MPP_FLAGS_LAST_MSG_LOCAL	0x00000002u

/* RKVENC_CLASS_BASE, from the driver's own hardware description. */
#define CLASS_BASE_S			0x0000u
#define CLASS_BASE_E			0x0058u

/* MPP_MAX_REG_TRANS_NUM, from the driver. */
#define MAX_TRANS_NUM			60

#define MAX_CASES			32

struct msg_v1 {
	uint32_t cmd;
	uint32_t flags;
	uint32_t size;
	uint32_t offset;
	uint64_t data_ptr;
};

struct expectation {
	char name[64];
	int err;		/* 0 means the request must SUCCEED */
	bool seen;
};

static struct expectation expectations[MAX_CASES];
static size_t expectation_count;

static int failures;

static void fail(const char *fmt, ...)
{
	va_list ap;

	failures++;
	fputs("  FAIL ", stderr);
	va_start(ap, fmt);
	vfprintf(stderr, fmt, ap);
	va_end(ap);
	fputc('\n', stderr);
}

static void okay(const char *fmt, ...)
{
	va_list ap;

	fputs("  ok   ", stdout);
	va_start(ap, fmt);
	vfprintf(stdout, fmt, ap);
	va_end(ap);
	fputc('\n', stdout);
}

static int errno_from_name(const char *name)
{
	static const struct { const char *name; int err; } table[] = {
		{ "OK", 0 },
		{ "EINVAL", EINVAL },
		{ "EFAULT", EFAULT },
		{ "ENOMEM", ENOMEM },
		{ "ENODEV", ENODEV },
		{ "EBUSY", EBUSY },
		{ "EIO", EIO },
	};
	size_t i;

	for (i = 0; i < sizeof(table) / sizeof(table[0]); i++)
		if (!strcmp(table[i].name, name))
			return table[i].err;

	return -1;
}

static const char *name_from_errno(int err)
{
	switch (err) {
	case 0:		return "OK";
	case EINVAL:	return "EINVAL";
	case EFAULT:	return "EFAULT";
	case ENOMEM:	return "ENOMEM";
	case ENODEV:	return "ENODEV";
	case EBUSY:	return "EBUSY";
	case EIO:	return "EIO";
	default:	return "OTHER";
	}
}

/*
 * The table is validated STRUCTURALLY before any of it is trusted: unknown
 * errno names, duplicate cases and malformed rows are all rejected here rather
 * than producing a case that silently expects nothing.
 */
static int load_expectations(const char *path)
{
	char line[512];
	FILE *fp = fopen(path, "r");
	size_t lineno = 0;

	if (!fp) {
		fprintf(stderr, "ERROR cannot open expectation table %s: %s\n",
			path, strerror(errno));
		return -1;
	}

	while (fgets(line, sizeof(line), fp)) {
		char *name, *err_name, *what, *nl;
		size_t i;
		int err;

		lineno++;
		nl = strchr(line, '\n');
		if (nl)
			*nl = '\0';
		if (line[0] == '#' || line[0] == '\0')
			continue;

		name = line;
		err_name = strchr(name, '\t');
		if (!err_name) {
			fprintf(stderr, "ERROR %s:%zu: not tab-separated\n", path, lineno);
			fclose(fp);
			return -1;
		}
		*err_name++ = '\0';
		what = strchr(err_name, '\t');
		if (!what) {
			fprintf(stderr, "ERROR %s:%zu: missing the third column\n",
				path, lineno);
			fclose(fp);
			return -1;
		}
		*what++ = '\0';

		if (!strcmp(name, "case"))	/* the header row */
			continue;
		if (*what == '\0') {
			fprintf(stderr, "ERROR %s:%zu: empty description\n", path, lineno);
			fclose(fp);
			return -1;
		}

		err = errno_from_name(err_name);
		if (err < 0) {
			fprintf(stderr, "ERROR %s:%zu: unknown errno name '%s'\n",
				path, lineno, err_name);
			fclose(fp);
			return -1;
		}
		for (i = 0; i < expectation_count; i++) {
			if (!strcmp(expectations[i].name, name)) {
				fprintf(stderr, "ERROR %s:%zu: duplicate case '%s'\n",
					path, lineno, name);
				fclose(fp);
				return -1;
			}
		}
		if (expectation_count == MAX_CASES) {
			fprintf(stderr, "ERROR %s:%zu: more than %d cases\n",
				path, lineno, MAX_CASES);
			fclose(fp);
			return -1;
		}
		if (strlen(name) >= sizeof(expectations[expectation_count].name)) {
			fprintf(stderr, "ERROR %s:%zu: case name too long\n",
				path, lineno);
			fclose(fp);
			return -1;
		}
		strcpy(expectations[expectation_count].name, name);
		expectations[expectation_count].err = err;
		expectations[expectation_count].seen = false;
		expectation_count++;
	}
	fclose(fp);

	if (!expectation_count) {
		fprintf(stderr, "ERROR %s declares no cases\n", path);
		return -1;
	}

	return 0;
}

static struct expectation *expectation_for(const char *name)
{
	size_t i;

	for (i = 0; i < expectation_count; i++)
		if (!strcmp(expectations[i].name, name))
			return &expectations[i];

	return NULL;
}

static int submit(int fd, struct msg_v1 *msgs, size_t count)
{
	size_t i;

	for (i = 0; i < count; i++) {
		msgs[i].flags |= MPP_FLAGS_MULTI_MSG_LOCAL;
		if (i + 1 == count)
			msgs[i].flags |= MPP_FLAGS_LAST_MSG_LOCAL;
	}

	errno = 0;
	if (ioctl(fd, MPP_IOC_CFG_V1, msgs) < 0)
		return errno;

	return 0;
}

/* Every case needs the session attached first, or it is rejected for a reason
 * that has nothing to do with what it is testing.
 */
static int attach_session(int fd)
{
	uint32_t client_type = 0;	/* MPP_DEVICE_RKVENC */
	struct msg_v1 msg = {
		.cmd = MPP_CMD_INIT_CLIENT_TYPE,
		.size = sizeof(client_type),
		.data_ptr = (uint64_t)(uintptr_t)&client_type,
	};

	return submit(fd, &msg, 1);
}

static void run_case(const char *name, int actual)
{
	struct expectation *want = expectation_for(name);

	if (!want) {
		fail("%s: no row in the expectation table", name);
		return;
	}
	want->seen = true;

	if (actual == want->err) {
		okay("%s -> %s", name, name_from_errno(actual));
		return;
	}
	fail("%s: expected %s, got %s (%d)", name, name_from_errno(want->err),
	     name_from_errno(actual), actual);
}

static void case_offset_size_wrap(int fd)
{
	uint32_t payload[8] = { 0 };
	struct msg_v1 msg = {
		.cmd = MPP_CMD_SET_REG_WRITE,
		.offset = 0xfffffff0u,
		.size = 0x20u,		/* offset + size wraps */
		.data_ptr = (uint64_t)(uintptr_t)payload,
	};

	run_case("offset-size-wrap", submit(fd, &msg, 1));
}

static void case_undersized_word(int fd)
{
	uint32_t payload[8] = { 0 };
	struct msg_v1 msg = {
		.cmd = MPP_CMD_SET_REG_WRITE,
		.offset = CLASS_BASE_S,
		.size = 1u,		/* offset + size - 4 underflows */
		.data_ptr = (uint64_t)(uintptr_t)payload,
	};

	run_case("undersized-word", submit(fd, &msg, 1));
}

static void case_unaligned_offset(int fd)
{
	uint32_t payload[8] = { 0 };
	struct msg_v1 msg = {
		.cmd = MPP_CMD_SET_REG_WRITE,
		.offset = CLASS_BASE_S + 2u,	/* not dword aligned */
		.size = 8u,
		.data_ptr = (uint64_t)(uintptr_t)payload,
	};

	run_case("unaligned-offset", submit(fd, &msg, 1));
}

/*
 * Starts one dword INSIDE the class and claims far more than the class holds.
 * The write path bounds this; the read path is where it used to over-read the
 * kernel heap into userspace.
 */
static void case_class_overrun(int fd)
{
	uint32_t payload[512] = { 0 };
	struct msg_v1 msgs[2] = {
		{
			.cmd = MPP_CMD_SET_REG_WRITE,
			.offset = CLASS_BASE_S,
			.size = CLASS_BASE_E - CLASS_BASE_S + 4u,
			.data_ptr = (uint64_t)(uintptr_t)payload,
		},
		{
			.cmd = MPP_CMD_SET_REG_READ,
			.offset = CLASS_BASE_S + 4u,
			.size = 0x4000u,	/* far past the class end */
			.data_ptr = (uint64_t)(uintptr_t)payload,
		},
	};

	run_case("class-overrun", submit(fd, msgs, 2));
}

static void case_invalid_metadata(int fd)
{
	uint8_t payload[13] = { 0 };	/* not a whole number of elements */
	struct msg_v1 msg = {
		.cmd = MPP_CMD_SET_REG_ADDR_OFFSET,
		.size = sizeof(payload),
		.data_ptr = (uint64_t)(uintptr_t)payload,
	};

	run_case("invalid-metadata", submit(fd, &msg, 1));
}

static void case_trans_table_odd_size(int fd)
{
	uint8_t payload[MAX_TRANS_NUM * 2 + 1];
	struct msg_v1 msg = {
		.cmd = MPP_CMD_INIT_TRANS_TABLE,
		.size = sizeof(payload),
		.data_ptr = (uint64_t)(uintptr_t)payload,
	};

	memset(payload, 0, sizeof(payload));
	run_case("trans-table-odd-size", submit(fd, &msg, 1));
}

/*
 * A PROT_NONE mapping is a genuinely unreadable user address, unlike a wild
 * constant which may happen to be mapped.
 */
static void case_bad_user_pointer(int fd)
{
	void *no_access = mmap(NULL, 4096, PROT_NONE,
			       MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
	struct msg_v1 msg;

	if (no_access == MAP_FAILED) {
		fail("bad-user-pointer: could not create a PROT_NONE mapping: %s",
		     strerror(errno));
		return;
	}
	memset(&msg, 0, sizeof(msg));
	msg.cmd = MPP_CMD_SET_REG_WRITE;
	msg.offset = CLASS_BASE_S;
	msg.size = 16u;
	msg.data_ptr = (uint64_t)(uintptr_t)no_access;

	run_case("bad-user-pointer", submit(fd, &msg, 1));
	munmap(no_access, 4096);
}

static void case_valid_after_failures(int fd)
{
	uint32_t payload[(CLASS_BASE_E - CLASS_BASE_S) / 4 + 1];
	struct msg_v1 msg = {
		.cmd = MPP_CMD_SET_REG_WRITE,
		.offset = CLASS_BASE_S,
		.size = sizeof(payload),
		.data_ptr = (uint64_t)(uintptr_t)payload,
	};

	memset(payload, 0, sizeof(payload));
	run_case("valid-after-failures", submit(fd, &msg, 1));
}

/*
 * The one case that is not about request SHAPE: it arms 0013's
 * fail_session_alloc_once and proves the attach failure is reported as -ENOMEM
 * rather than swallowed, and that the FOLLOWING open succeeds.
 */
static int case_session_allocation(const char *device, const char *debugfs)
{
	char path[512];
	FILE *fp;
	int fd, err;

	snprintf(path, sizeof(path), "%s/fail_session_alloc_once", debugfs);
	fp = fopen(path, "w");
	if (!fp) {
		fail("session-allocation-failure: cannot arm %s: %s",
		     path, strerror(errno));
		return -1;
	}
	fputs("1\n", fp);
	fclose(fp);

	fd = open(device, O_RDWR);
	if (fd < 0) {
		fail("session-allocation-failure: cannot open %s: %s",
		     device, strerror(errno));
		return -1;
	}
	err = attach_session(fd);
	run_case("session-allocation-failure", err);
	close(fd);

	/* The knob is one-shot, so the next open must attach cleanly. */
	fd = open(device, O_RDWR);
	if (fd < 0) {
		fail("session-allocation-failure: the FOLLOWING open failed: %s",
		     strerror(errno));
		return -1;
	}
	err = attach_session(fd);
	if (err)
		fail("session-allocation-failure: the following attach failed with %s",
		     name_from_errno(err));
	else
		okay("the following open/attach succeeds (the knob is one-shot)");
	close(fd);

	return 0;
}

static void usage(void)
{
	fputs("usage: rkvenc-invalid-ioctl --device <dev> "
	      "[--all-malformed | --case <name>] "
	      "[--expect-table <tsv>] [--debugfs <dir>]\n", stderr);
}

int main(int argc, char **argv)
{
	const char *device = "/dev/mpp_service";
	const char *table = "/tmp/ceralive-qa/expected-errno.tsv";
	const char *debugfs = "/sys/kernel/debug/rkvenc-test";
	const char *only = NULL;
	bool all = false;
	int fd, i;
	size_t c;

	for (i = 1; i < argc; i++) {
		if (!strcmp(argv[i], "--device") && i + 1 < argc)
			device = argv[++i];
		else if (!strcmp(argv[i], "--expect-table") && i + 1 < argc)
			table = argv[++i];
		else if (!strcmp(argv[i], "--debugfs") && i + 1 < argc)
			debugfs = argv[++i];
		else if (!strcmp(argv[i], "--case") && i + 1 < argc)
			only = argv[++i];
		else if (!strcmp(argv[i], "--all-malformed"))
			all = true;
		else {
			usage();
			return 2;
		}
	}
	if (!all && !only) {
		usage();
		return 2;
	}

	if (load_expectations(table))
		return 2;

	if (only && !strcmp(only, "session-allocation-failure")) {
		if (case_session_allocation(device, debugfs))
			return 1;
		goto done;
	}

	fd = open(device, O_RDWR);
	if (fd < 0) {
		fprintf(stderr, "ERROR cannot open %s: %s\n", device, strerror(errno));
		return 2;
	}
	if (attach_session(fd)) {
		fprintf(stderr, "ERROR cannot attach a session on %s: %s\n",
			device, strerror(errno));
		close(fd);
		return 2;
	}

	if (all) {
		case_offset_size_wrap(fd);
		case_undersized_word(fd);
		case_unaligned_offset(fd);
		case_class_overrun(fd);
		case_invalid_metadata(fd);
		case_trans_table_odd_size(fd);
		case_bad_user_pointer(fd);
		/*
		 * LAST, deliberately: the claim is not merely that each
		 * malformed request is rejected, but that the session is still
		 * usable after every one of them.
		 */
		case_valid_after_failures(fd);

		for (c = 0; c < expectation_count; c++) {
			if (expectations[c].seen)
				continue;
			if (!strcmp(expectations[c].name, "session-allocation-failure"))
				continue;	/* has its own invocation */
			fail("table row '%s' was never exercised",
			     expectations[c].name);
		}
	} else {
		fprintf(stderr, "ERROR unknown case: %s\n", only);
		close(fd);
		return 2;
	}
	close(fd);

done:
	if (failures) {
		fprintf(stderr, "RESULT=FAIL case=rkvenc-invalid-ioctl failures=%d\n",
			failures);
		return 1;
	}
	printf("RESULT=PASS case=rkvenc-invalid-ioctl cases=%zu table=%s\n",
	       expectation_count, table);

	return 0;
}
