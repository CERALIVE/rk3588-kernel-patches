"""Execute the real audio helpers with deterministic register/clock failures."""

from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
DRIVER = Path("drivers/media/platform/synopsys/hdmirx/snps_hdmirx.c")
TREE: Path | None = None


def additions(path: str) -> str:
    return "\n".join(line[1:] for line in (ROOT / path).read_text().splitlines()
                     if line.startswith("+") and not line.startswith("+++"))


def function(source: str, name: str, patches: tuple[str, ...] = ()) -> str:
    code = source + "\n"
    for patch in patches:
        for header, body in re.findall(r"^(@@.*?@@[^\n]*)\n(.*?)(?=^@@|^diff --git|\Z)",
                                       patch, re.M | re.S):
            before = "".join(line[1:] + "\n" for line in body.splitlines()
                             if line.startswith((" ", "-")))
            after = "".join(line[1:] + "\n" for line in body.splitlines()
                            if line.startswith((" ", "+")))
            if before not in code:
                assert name not in header, f"Unmatched helper hunk: {header}"
                continue
            assert code.count(before) == 1, f"Unmatched helper hunk: {header}"
            code = code.replace(before, after, 1)
    match = re.search(r"static [^\n]+ " + name + r"\([^;]*?\)\n\{.*?\n\}", code, re.S)
    if match is None:
        raise AssertionError(f"Missing complete helper: {name}")
    return match.group()


PRELUDE = r"""
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
typedef uint32_t u32;
typedef uint64_t u64;
enum { CMU_TMDSQPCLK_FREQ, PKTDEC_ACR_PH2_1, PKTDEC_ACR_PB3_0,
       PKTDEC_ACR_PB7_4, AUDIO_PROC_CONFIG0, AUDIO_PROC_CONFIG3,
       PKTDEC_AUDIF_PH2_1, PKTDEC_AUDIF_PB3_0, AUDIO_FIFO_STATUS2,
       AUDIO_FIFO_CONTROL, REG_COUNT };
enum { EINVAL = 22, EIO = 5, I2S_EN = 2, SPEAKER_ALLOC_OVR_EN = 65536 };
enum { AFIFO_UNDERFLOW_ST = 1 << 25, AFIFO_OVERFLOW_ST = 1 << 24,
       HDMIRX_AUDIO_INIT_STATE = 512 };
struct work_struct { int unused; };
struct delayed_work { struct work_struct work; };
struct snps_hdmirx_dev {
    void *dev, *audio_clk;
    u32 audio_fs, audio_clkrate, audio_channels;
    bool audio_running, audio_streaming;
    int audio_lock, audio_pre_state;
    struct delayed_work audio_work;
    void (*plugged_cb)(void *, bool);
    void *codec_dev;
};
static u32 regs[REG_COUNT], clock_rate;
static int clock_error, clock_calls, drains, fifo_writes, notifications, queued;
static unsigned long queued_delay;
static struct snps_hdmirx_dev *draining;
#define container_of(p, t, m) ((t *)((char *)(p) - offsetof(t, m)))
#define to_delayed_work(p) container_of(p, struct delayed_work, work)
#define system_unbound_wq NULL
#define msecs_to_jiffies(x) (x)
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x, v) ((x) = (v))
#define lockdep_assert_held(x) assert(*(x) == 1)
#define dev_err_ratelimited(...) ((void)0)
#define dev_warn_ratelimited(...) ((void)0)
#define snd_ctl_notify(...) (notifications++)
#define snd_pcm_stop_xrun(...) (notifications++)
#define v4l2_event_queue(...) (notifications++)
#define swab32(x) __builtin_bswap32(x)
static u64 div_u64(u64 n, u32 d) { return n / d; }
#define div64_u64(n, d) ((n) / (d))
static u32 hdmirx_readl(struct snps_hdmirx_dev *d, int reg)
{ (void)d; return regs[reg]; }
static void hdmirx_writel(struct snps_hdmirx_dev *d, int reg, u32 value)
{
    (void)d;
    if (reg == AUDIO_FIFO_CONTROL) {
        assert(value == (fifo_writes % 2 == 0 ? 1U : 0U));
        fifo_writes++;
    }
    regs[reg] = value;
}
static void hdmirx_update_bits(struct snps_hdmirx_dev *d, int reg, u32 mask, u32 v)
{ (void)d; regs[reg] = (regs[reg] & ~mask) | v; }
static int clk_set_rate(void *clk, u32 rate)
{ (void)clk; clock_rate = rate; clock_calls++; return clock_error; }
static void cancel_delayed_work_sync(struct delayed_work *work)
{ (void)work; assert(!draining->audio_running); drains++; }
static void usleep_range(int low, int high)
{ assert(low == 200 && high == 210 && regs[AUDIO_FIFO_CONTROL] == 1); }
static void queue_delayed_work(void *q, struct delayed_work *work, unsigned long delay)
{ (void)q; (void)work; queued++; queued_delay = delay; }
static void notify(void *dev, bool present)
{ (void)dev; (void)present; notifications++; }
static void source_audio(u32 fs, u32 channels, u32 coding_type)
{
    /* 148.5 MHz TMDS; CTS/N pairs recover exact source rates. */
    regs[CMU_TMDSQPCLK_FREQ] = 37125;
    regs[PKTDEC_ACR_PB3_0] = swab32(fs == 44100 ? 165000 : 148500);
    regs[PKTDEC_ACR_PB7_4] = swab32((fs == 44100 ? 6272 : fs * 128 / 1000) << 8);
    regs[PKTDEC_AUDIF_PB3_0] = ((channels - 1) << 8) | (coding_type << 4);
}
"""

MAIN = r"""
int main(int argc, char **argv)
{
    struct snps_hdmirx_dev d = { .audio_fs = 44100, .audio_clkrate = 5644800,
                               .audio_running = true, .audio_streaming = true,
                               .audio_channels = 2, .audio_lock = 1,
                               .plugged_cb = notify };
    assert(argc == 2);
    switch (atoi(argv[1])) {
    case 0:
        clock_error = -EIO;
        assert(hdmirx_audio_set_fs(&d, 48000) == -EIO);
        assert(d.audio_fs == 44100 && d.audio_clkrate == 5644800);
        assert(clock_calls == 1);
        break;
    case 1:
        assert(hdmirx_audio_set_fs(&d, 48000) == 0);
        assert(d.audio_fs == 48000 && d.audio_clkrate == 6144000);
        break;
    case 2:
        assert(hdmirx_audio_closest_fs(768000) == 0);
        assert(hdmirx_audio_set_fs(&d, 768000) == -EINVAL);
        assert(hdmirx_audio_set_fs(&d, 0) == -EINVAL);
        assert(hdmirx_audio_set_fs(&d, 48001) == -EINVAL);
        assert(clock_calls == 0);
        break;
    case 3:
        /* 148.5 MHz, CTS=148500 (0x24414), N=6144 (0x1800). */
        regs[CMU_TMDSQPCLK_FREQ] = 37125;
        regs[PKTDEC_ACR_PB3_0] = 0x14440200;
        regs[PKTDEC_ACR_PB7_4] = 0x00001800;
        assert(hdmirx_audio_fs(&d) == 48000);
        /* CTS=165000, N=6272 recovers 44.1 kHz, not a fallback. */
        regs[PKTDEC_ACR_PB3_0] = 0x88840200;
        regs[PKTDEC_ACR_PB7_4] = 0x00801800;
        assert(hdmirx_audio_fs(&d) == 44100);
        regs[PKTDEC_ACR_PB3_0] = 0;
        assert(hdmirx_audio_fs(&d) == 0);
        break;
    case 4:
        draining = &d;
        hdmirx_audio_stop(&d);
        assert(!d.audio_running && drains == 1);
        break;
    case 5:
        hdmirx_audio_route(&d, 8);
        assert(d.audio_channels == 8);
        assert(regs[AUDIO_PROC_CONFIG0] == (SPEAKER_ALLOC_OVR_EN | I2S_EN));
        assert(regs[AUDIO_PROC_CONFIG3] == 0xffffffff);
        hdmirx_audio_route(&d, 2);
        assert(d.audio_channels == 2 && regs[AUDIO_PROC_CONFIG0] == I2S_EN);
        break;
    case 6: {
        const u32 rates[] = { 44100, 48000, 96000 };
        for (unsigned int from = 0; from < 3; from++)
            for (unsigned int to = 0; to < 3; to++) {
                if (from == to)
                    continue;
                d.audio_fs = rates[from];
                d.audio_clkrate = rates[from] * 128;
                d.audio_pre_state = 600;
                source_audio(rates[to], 2, 1);
                regs[AUDIO_FIFO_STATUS2] = 600;
                int writes = fifo_writes, calls = clock_calls, runs = queued;
                hdmirx_audio_work(&d.audio_work.work);
                assert(d.audio_fs == rates[to] && clock_rate == rates[to] * 128);
                assert(d.audio_clkrate == clock_rate && clock_calls == calls + 1);
                assert(fifo_writes == writes + 2 && d.audio_pre_state == 0);
                assert(d.audio_running && d.audio_streaming && notifications == 0);
                assert(queued == runs + 1 && queued_delay == 200);
            }
        break;
    }
    case 7:
        for (int i = 0; i < 2; i++) {
            u32 channels = i == 0 ? 8 : 2;
            source_audio(44100, channels, 1);
            d.audio_pre_state = 600;
            int writes = fifo_writes, runs = queued;
            hdmirx_audio_work(&d.audio_work.work);
            assert(d.audio_channels == channels && d.audio_fs == 44100);
            assert(regs[AUDIO_PROC_CONFIG0] ==
                   (I2S_EN | (channels > 2 ? SPEAKER_ALLOC_OVR_EN : 0)));
            if (channels > 2)
                assert(regs[AUDIO_PROC_CONFIG3] == 0xffffffff);
            assert(fifo_writes == writes + 2 && d.audio_pre_state == 0);
            assert(d.audio_running && d.audio_streaming && notifications == 0);
            assert(queued == runs + 1 && queued_delay == 200);
        }
        break;
    case 8:
        /* AC-3's coding type is ignored: a supported recovered rate is adopted. */
        source_audio(48000, 2, 2);
        hdmirx_audio_work(&d.audio_work.work);
        assert(d.audio_fs == 48000 && d.audio_clkrate == 6144000);
        assert(fifo_writes == 2 && d.audio_pre_state == 0 && queued_delay == 200);
        /* HBR's 768 kHz transport rate is invalid, leaving the stream armed. */
        source_audio(768000, 8, 9);
        d.audio_pre_state = 600;
        regs[AUDIO_FIFO_STATUS2] = 700;
        hdmirx_audio_work(&d.audio_work.work);
        assert(d.audio_fs == 48000 && d.audio_channels == 2 && clock_calls == 1);
        assert(fifo_writes == 2 && d.audio_pre_state == 600 && queued_delay == 1000);
        assert(queued == 2 && d.audio_running && d.audio_streaming && notifications == 0);
        break;
    case 9: {
        const u32 faults[] = { AFIFO_UNDERFLOW_ST, AFIFO_OVERFLOW_ST,
                              AFIFO_UNDERFLOW_ST | AFIFO_OVERFLOW_ST };
        for (unsigned int i = 0; i < 3; i++)
            for (unsigned int valid = 0; valid < 2; valid++) {
                source_audio(valid ? 96000 : 768000, 8, valid ? 1 : 9);
                d.audio_fs = 44100;
                d.audio_clkrate = 5644800;
                d.audio_channels = 2;
                d.audio_pre_state = 600;
                regs[AUDIO_FIFO_STATUS2] = faults[i] | 700;
                int writes = fifo_writes, calls = clock_calls, runs = queued;
                hdmirx_audio_work(&d.audio_work.work);
                assert(fifo_writes == writes + 2 && d.audio_pre_state == 0);
                assert(d.audio_fs == (valid ? 96000U : 44100U));
                assert(d.audio_channels == (valid ? 8U : 2U));
                assert(d.audio_clkrate == (valid ? 12288000U : 5644800U));
                assert(clock_calls == calls + (int)valid);
                assert(d.audio_running && d.audio_streaming && notifications == 0);
                assert(queued == runs + 1 && queued_delay == 200);
            }
        break;
    }
    default: abort();
    }
    return 0;
}
"""


class AudioHelpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="hdmirx-audio-")
        cls.addClassCleanup(cls.temp.cleanup)
        directory = Path(cls.temp.name)
        cls.binary = directory / "audio-test"
        upstream = additions("backports/0043-hdmirx-audio-v4-2.patch")
        clock = additions("ceralive/0046-hdmirx-audio-clock-errors-and-rates.patch")
        lifecycle = additions("ceralive/0047-hdmirx-audio-worker-lifetime.patch")
        channels = additions("ceralive/0048-hdmirx-audio-channel-routing.patch")
        table = re.search(r"\t32000,[^\n]+", clock)
        assert table is not None
        rate_table = "static const int hdmirx_supported_fs[] = {" + table.group() + "};\n"
        if TREE:
            actual = re.search(r"static const int hdmirx_supported_fs\[\] = \{.*?\};",
                               (TREE / DRIVER).read_text(), re.S)
            assert actual is not None
            rate_table = actual.group() + "\n"
        deltas = tuple((ROOT / path).read_text() for path in (
            "ceralive/0046-hdmirx-audio-clock-errors-and-rates.patch",
            "ceralive/0047-hdmirx-audio-worker-lifetime.patch",
            "ceralive/0048-hdmirx-audio-channel-routing.patch",
        ))
        source = PRELUDE + rate_table
        for text, name in (
            (upstream, "hdmirx_audio_closest_fs"),
            (upstream, "hdmirx_audio_fs"),
            (clock, "hdmirx_audio_set_fs"),
            (lifecycle, "hdmirx_audio_stop"),
            (channels, "hdmirx_audio_route"),
            (channels, "hdmirx_audio_channels"),
            (upstream, "hdmirx_audio_clk_ppm_inc"),
            (upstream, "hdmirx_audio_clk_adjust"),
            (upstream, "hdmirx_audio_fifo_reinit"),
            (upstream, "hdmirx_audio_work"),
        ):
            source += function((TREE / DRIVER).read_text() if TREE else text, name,
                               deltas if not TREE and name in (
                                   "hdmirx_audio_work", "hdmirx_audio_clk_ppm_inc",
                               ) else ()) + "\n"
        program = directory / "audio-test.c"
        program.write_text(source + MAIN)
        subprocess.run(["cc", "-std=gnu11", "-Wall", "-Wextra", "-Werror",
                        str(program), "-o", str(cls.binary)], check=True)

    def run_case(self, case: int) -> None:
        subprocess.run([str(self.binary), str(case)], check=True)

    def test_refused_clock_preserves_state(self) -> None:
        self.run_case(0)

    def test_success_publishes_real_clock(self) -> None:
        self.run_case(1)

    def test_invalid_rates_never_reach_clock(self) -> None:
        self.run_case(2)

    def test_acr_byte_order_recovers_both_rates(self) -> None:
        self.run_case(3)

    def test_disarm_precedes_synchronous_drain(self) -> None:
        self.run_case(4)

    def test_multichannel_to_stereo_clears_override(self) -> None:
        self.run_case(5)

    def test_open_stream_adopts_live_rate_changes_and_resets_fifo(self) -> None:
        self.run_case(6)

    def test_open_stream_reroutes_live_channel_changes_and_resets_fifo(self) -> None:
        self.run_case(7)

    def test_non_pcm_ignores_coding_type_but_backs_off_on_hbr_rate(self) -> None:
        self.run_case(8)

    def test_fifo_faults_reset_even_with_invalid_rate_and_keep_worker_armed(self) -> None:
        self.run_case(9)

    def test_canonical_trailing_context_is_valid_mailbox(self) -> None:
        subprocess.run(["git", "apply", "--numstat",
                        str(ROOT / "patches/0044-hdmirx-audio-v4-3.patch")],
                       check=True, capture_output=True)


def verify_applied_tree(tree: Path) -> None:
    source = (tree / DRIVER).read_text()
    remove = function(source, "hdmirx_remove")
    assert remove.index("audio_removing = true") < remove.index("hdmirx_audio_stop(")
    assert remove.index("hdmirx_audio_stop(") < remove.index("platform_device_unregister(")
    edid = function(source, "hdmirx_set_edid")
    assert edid.index("return -EBUSY") < edid.index("hdmirx_audio_link(")
    assert edid.index("hdmirx_audio_link(") < edid.index("disable_irq(")
    worker = function(source, "hdmirx_audio_work")
    assert "mutex_lock(" not in worker and "plugged_cb" not in worker
    assert worker.index("audio_running") < worker.index("hdmirx_audio_fs(")
    assert "if (READ_ONCE(hdmirx_dev->audio_running))" in worker
    assert "clk_set_rate(" not in worker
    assert "ret = hdmirx_audio_setup(" in function(source, "hdmirx_audio_hw_params")
    assert "ret = hdmirx_audio_setup(" in function(source, "hdmirx_resume")
    dts = tree / "arch/arm64/boot/dts/rockchip"
    card = (dts / "rk3588-extra.dtsi").read_text()
    assert 'simple-audio-card,name = "RK3588 HDMI-IN";' in card
    assert 'sound-dai = <&hdmi_receiver 0>;' in card
    for board in ("rk3588-rock-5b.dtsi", "rk3588-orangepi-5-plus.dts"):
        text = (dts / board).read_text()
        for node in ("hdmi_receiver_sound", "i2s7_8ch"):
            assert re.search(r"&" + node + r'\s*\{\s*status = "okay";\s*\};', text)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--tree":
        TREE = Path(sys.argv[2])
        verify_applied_tree(TREE)
        sys.argv = sys.argv[:1]
    unittest.main()
