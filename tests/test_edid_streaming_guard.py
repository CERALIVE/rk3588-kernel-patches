"""Execute the source-lane guard in a tiny queue shim, without hardware."""

from pathlib import Path
import subprocess
import tempfile
import unittest


class EdidStreamingGuardTests(unittest.TestCase):
    def test_streaming_refuses_mutation_and_idle_proceeds(self) -> None:
        patch = Path(__file__).resolve().parents[1] / (
            "ceralive/0040-hdmirx-refuse-edid-while-streaming.patch"
        )
        added = "\n".join(
            line[1:] for line in patch.read_text().splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        source = """
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
struct queue { bool streaming; };
struct stream { struct queue buf_queue; };
static bool vb2_is_streaming(struct queue *q) { return q->streaming; }
static int set_edid(struct stream *stream, int *bytes)
{
GUARD
    *bytes = 42;
    return 0;
}
int main(void)
{
    struct stream stream = { .buf_queue.streaming = true };
    int bytes = 17;
    assert(set_edid(&stream, &bytes) == -EBUSY);
    assert(bytes == 17);
    stream.buf_queue.streaming = false;
    assert(set_edid(&stream, &bytes) == 0);
    assert(bytes == 42);
}
""".replace("GUARD", added)
        with tempfile.TemporaryDirectory() as directory:
            c_file = Path(directory) / "guard.c"
            binary = Path(directory) / "guard"
            c_file.write_text(source)
            subprocess.run(
                ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                 str(c_file), "-o", str(binary)], check=True,
            )
            subprocess.run([str(binary)], check=True)
