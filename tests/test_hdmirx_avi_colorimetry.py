"""Exercise the source-lane AVI colorimetry table, without hardware.

The mapping function is pure -- every input is an argument -- so the whole
CTA-861 table is reachable from a workstation. This lifts that function out of
the patch verbatim, compiles it against the REAL uapi V4L2 enums, and asserts
every row, both fallback rows, and the DVI no-InfoFrame row.
"""

from pathlib import Path
import subprocess
import tempfile
import unittest

PATCH = "ceralive/0041-hdmirx-avi-colorimetry.patch"

STRUCT_OPEN = "struct hdmirx_colorimetry {"
STRUCT_CLOSE = "};"
MAP_SIGNATURE = "hdmirx_avi_colorimetry(u8 c, u8 ec, u8 q, u8 yq, bool is_rgb,"
MAP_RETURN = "static struct hdmirx_colorimetry"
AFTER_LAST_PURE_FN = "static void hdmirx_set_colorimetry("

# linux/hdmi.h is not a uapi header, so the harness restates the four AVI
# enumerations it needs. Their values ARE the raw CTA-861 bit patterns, which
# is exactly what hdmi_infoframe_unpack() writes into the frame.
PREAMBLE = """
#include <stdbool.h>
#include <stdio.h>
#include <time.h>

#include <linux/videodev2.h>

typedef unsigned char u8;

enum hdmi_colorimetry {
\tHDMI_COLORIMETRY_NONE,
\tHDMI_COLORIMETRY_ITU_601,
\tHDMI_COLORIMETRY_ITU_709,
\tHDMI_COLORIMETRY_EXTENDED,
};

enum hdmi_extended_colorimetry {
\tHDMI_EXTENDED_COLORIMETRY_XV_YCC_601,
\tHDMI_EXTENDED_COLORIMETRY_XV_YCC_709,
\tHDMI_EXTENDED_COLORIMETRY_S_YCC_601,
\tHDMI_EXTENDED_COLORIMETRY_OPYCC_601,
\tHDMI_EXTENDED_COLORIMETRY_OPRGB,
\tHDMI_EXTENDED_COLORIMETRY_BT2020_CONST_LUM,
\tHDMI_EXTENDED_COLORIMETRY_BT2020,
\tHDMI_EXTENDED_COLORIMETRY_RESERVED,
};

enum hdmi_quantization_range {
\tHDMI_QUANTIZATION_RANGE_DEFAULT,
\tHDMI_QUANTIZATION_RANGE_LIMITED,
\tHDMI_QUANTIZATION_RANGE_FULL,
\tHDMI_QUANTIZATION_RANGE_RESERVED,
};

enum hdmi_ycc_quantization_range {
\tHDMI_YCC_QUANTIZATION_RANGE_LIMITED,
\tHDMI_YCC_QUANTIZATION_RANGE_FULL,
};
"""

DRIVER = r"""
static int failures;

static void expect(const char *row, struct hdmirx_colorimetry got,
		   unsigned int colorspace, unsigned int ycbcr_enc,
		   unsigned int xfer_func, unsigned int quantization)
{
	if (got.colorspace != colorspace) {
		printf("%s: colorspace %d, want %d\n", row,
		       (int)got.colorspace, colorspace);
		failures++;
	}
	if (got.ycbcr_enc != ycbcr_enc) {
		printf("%s: ycbcr_enc %d, want %d\n", row,
		       (int)got.ycbcr_enc, ycbcr_enc);
		failures++;
	}
	if (got.xfer_func != xfer_func) {
		printf("%s: xfer_func %d, want %d\n", row,
		       (int)got.xfer_func, xfer_func);
		failures++;
	}
	if (got.quantization != quantization) {
		printf("%s: quantization %d, want %d\n", row,
		       (int)got.quantization, quantization);
		failures++;
	}
}

/* Isolate the C/EC rows: q=0 and yq=2 both map to DEFAULT quantization. */
#define RGB(row, c, ec, cs, enc, xf) \
	expect(row, hdmirx_avi_colorimetry((c), (ec), 0, 2, true, 1080), \
	       (cs), (enc), (xf), V4L2_QUANTIZATION_DEFAULT)
#define YCC(row, c, ec, h, cs, enc, xf) \
	expect(row, hdmirx_avi_colorimetry((c), (ec), 0, 2, false, (h)), \
	       (cs), (enc), (xf), V4L2_QUANTIZATION_DEFAULT)

int main(void)
{
	/* C=0 (no data), YCC: 601 at or below 576 active lines, 709 above. */
	YCC("C0/ycc/480", 0, 0, 480, V4L2_COLORSPACE_SMPTE170M,
	    V4L2_YCBCR_ENC_601, V4L2_XFER_FUNC_DEFAULT);
	YCC("C0/ycc/576", 0, 0, 576, V4L2_COLORSPACE_SMPTE170M,
	    V4L2_YCBCR_ENC_601, V4L2_XFER_FUNC_DEFAULT);
	YCC("C0/ycc/577", 0, 0, 577, V4L2_COLORSPACE_REC709,
	    V4L2_YCBCR_ENC_709, V4L2_XFER_FUNC_DEFAULT);
	YCC("C0/ycc/2160", 0, 0, 2160, V4L2_COLORSPACE_REC709,
	    V4L2_YCBCR_ENC_709, V4L2_XFER_FUNC_DEFAULT);

	/* C=0 (no data), RGB. */
	RGB("C0/rgb", 0, 0, V4L2_COLORSPACE_SRGB, V4L2_YCBCR_ENC_DEFAULT,
	    V4L2_XFER_FUNC_SRGB);

	/* C=1, SMPTE 170M. */
	YCC("C1/ycc", 1, 0, 1080, V4L2_COLORSPACE_SMPTE170M,
	    V4L2_YCBCR_ENC_601, V4L2_XFER_FUNC_709);
	RGB("C1/rgb", 1, 0, V4L2_COLORSPACE_SMPTE170M, V4L2_YCBCR_ENC_DEFAULT,
	    V4L2_XFER_FUNC_709);

	/* C=2, Rec. 709. */
	YCC("C2/ycc", 2, 0, 1080, V4L2_COLORSPACE_REC709,
	    V4L2_YCBCR_ENC_709, V4L2_XFER_FUNC_709);
	RGB("C2/rgb", 2, 0, V4L2_COLORSPACE_REC709, V4L2_YCBCR_ENC_DEFAULT,
	    V4L2_XFER_FUNC_709);

	/* C=3 EC=0, xvYCC601. */
	YCC("C3EC0/ycc", 3, 0, 1080, V4L2_COLORSPACE_SMPTE170M,
	    V4L2_YCBCR_ENC_XV601, V4L2_XFER_FUNC_709);
	RGB("C3EC0/rgb", 3, 0, V4L2_COLORSPACE_SMPTE170M,
	    V4L2_YCBCR_ENC_DEFAULT, V4L2_XFER_FUNC_709);

	/* C=3 EC=1, xvYCC709. */
	YCC("C3EC1/ycc", 3, 1, 1080, V4L2_COLORSPACE_REC709,
	    V4L2_YCBCR_ENC_XV709, V4L2_XFER_FUNC_709);
	RGB("C3EC1/rgb", 3, 1, V4L2_COLORSPACE_REC709, V4L2_YCBCR_ENC_DEFAULT,
	    V4L2_XFER_FUNC_709);

	/* C=3 EC=2, sYCC601. */
	YCC("C3EC2/ycc", 3, 2, 1080, V4L2_COLORSPACE_SRGB,
	    V4L2_YCBCR_ENC_601, V4L2_XFER_FUNC_SRGB);
	RGB("C3EC2/rgb", 3, 2, V4L2_COLORSPACE_SRGB, V4L2_YCBCR_ENC_DEFAULT,
	    V4L2_XFER_FUNC_SRGB);

	/* C=3 EC=3, AdobeYCC601. */
	YCC("C3EC3/ycc", 3, 3, 1080, V4L2_COLORSPACE_OPRGB,
	    V4L2_YCBCR_ENC_601, V4L2_XFER_FUNC_OPRGB);
	RGB("C3EC3/rgb", 3, 3, V4L2_COLORSPACE_OPRGB, V4L2_YCBCR_ENC_DEFAULT,
	    V4L2_XFER_FUNC_OPRGB);

	/* C=3 EC=4, AdobeRGB: DEFAULT encoding for both pixel encodings. */
	YCC("C3EC4/ycc", 3, 4, 1080, V4L2_COLORSPACE_OPRGB,
	    V4L2_YCBCR_ENC_DEFAULT, V4L2_XFER_FUNC_OPRGB);
	RGB("C3EC4/rgb", 3, 4, V4L2_COLORSPACE_OPRGB, V4L2_YCBCR_ENC_DEFAULT,
	    V4L2_XFER_FUNC_OPRGB);

	/* C=3 EC=5, BT.2020 cYCC. SDR transfer on purpose: no HDR path here. */
	YCC("C3EC5/ycc", 3, 5, 2160, V4L2_COLORSPACE_BT2020,
	    V4L2_YCBCR_ENC_BT2020_CONST_LUM, V4L2_XFER_FUNC_709);
	RGB("C3EC5/rgb", 3, 5, V4L2_COLORSPACE_BT2020, V4L2_YCBCR_ENC_DEFAULT,
	    V4L2_XFER_FUNC_709);

	/* C=3 EC=6, BT.2020 RGB or YCC. */
	YCC("C3EC6/ycc", 3, 6, 2160, V4L2_COLORSPACE_BT2020,
	    V4L2_YCBCR_ENC_BT2020, V4L2_XFER_FUNC_709);
	RGB("C3EC6/rgb", 3, 6, V4L2_COLORSPACE_BT2020, V4L2_YCBCR_ENC_DEFAULT,
	    V4L2_XFER_FUNC_709);

	/*
	 * C=3 EC=7, additional gamut. RGB takes DCI-P3 with the no-data row's
	 * transfer function; YCC has no reading and falls back whole.
	 */
	RGB("C3EC7/rgb", 3, 7, V4L2_COLORSPACE_DCI_P3, V4L2_YCBCR_ENC_DEFAULT,
	    V4L2_XFER_FUNC_SRGB);
	YCC("C3EC7/ycc/480", 3, 7, 480, V4L2_COLORSPACE_SMPTE170M,
	    V4L2_YCBCR_ENC_601, V4L2_XFER_FUNC_DEFAULT);
	YCC("C3EC7/ycc/1080", 3, 7, 1080, V4L2_COLORSPACE_REC709,
	    V4L2_YCBCR_ENC_709, V4L2_XFER_FUNC_DEFAULT);

	/* A colorimetry value outside the 2-bit field falls back, not garbage. */
	RGB("Cunknown/rgb", 9, 0, V4L2_COLORSPACE_SRGB, V4L2_YCBCR_ENC_DEFAULT,
	    V4L2_XFER_FUNC_SRGB);
	YCC("Cunknown/ycc/480", 9, 0, 480, V4L2_COLORSPACE_SMPTE170M,
	    V4L2_YCBCR_ENC_601, V4L2_XFER_FUNC_DEFAULT);
	YCC("Cunknown/ycc/1080", 9, 0, 1080, V4L2_COLORSPACE_REC709,
	    V4L2_YCBCR_ENC_709, V4L2_XFER_FUNC_DEFAULT);

	/* Likewise an extended value outside the 3-bit field. */
	RGB("ECunknown/rgb", 3, 9, V4L2_COLORSPACE_SRGB, V4L2_YCBCR_ENC_DEFAULT,
	    V4L2_XFER_FUNC_SRGB);
	YCC("ECunknown/ycc/480", 3, 9, 480, V4L2_COLORSPACE_SMPTE170M,
	    V4L2_YCBCR_ENC_601, V4L2_XFER_FUNC_DEFAULT);
	YCC("ECunknown/ycc/1080", 3, 9, 1080, V4L2_COLORSPACE_REC709,
	    V4L2_YCBCR_ENC_709, V4L2_XFER_FUNC_DEFAULT);

	/* RGB quantization comes from Q, and yq is ignored. */
	expect("Q0", hdmirx_avi_colorimetry(0, 0, 0, 1, true, 1080),
	       V4L2_COLORSPACE_SRGB, V4L2_YCBCR_ENC_DEFAULT,
	       V4L2_XFER_FUNC_SRGB, V4L2_QUANTIZATION_DEFAULT);
	expect("Q1", hdmirx_avi_colorimetry(0, 0, 1, 1, true, 1080),
	       V4L2_COLORSPACE_SRGB, V4L2_YCBCR_ENC_DEFAULT,
	       V4L2_XFER_FUNC_SRGB, V4L2_QUANTIZATION_LIM_RANGE);
	expect("Q2", hdmirx_avi_colorimetry(0, 0, 2, 0, true, 1080),
	       V4L2_COLORSPACE_SRGB, V4L2_YCBCR_ENC_DEFAULT,
	       V4L2_XFER_FUNC_SRGB, V4L2_QUANTIZATION_FULL_RANGE);
	expect("Q3", hdmirx_avi_colorimetry(0, 0, 3, 1, true, 1080),
	       V4L2_COLORSPACE_SRGB, V4L2_YCBCR_ENC_DEFAULT,
	       V4L2_XFER_FUNC_SRGB, V4L2_QUANTIZATION_DEFAULT);

	/* YCC quantization comes from YQ, and q is ignored. */
	expect("YQ0", hdmirx_avi_colorimetry(2, 0, 2, 0, false, 1080),
	       V4L2_COLORSPACE_REC709, V4L2_YCBCR_ENC_709,
	       V4L2_XFER_FUNC_709, V4L2_QUANTIZATION_LIM_RANGE);
	expect("YQ1", hdmirx_avi_colorimetry(2, 0, 1, 1, false, 1080),
	       V4L2_COLORSPACE_REC709, V4L2_YCBCR_ENC_709,
	       V4L2_XFER_FUNC_709, V4L2_QUANTIZATION_FULL_RANGE);
	expect("YQ2", hdmirx_avi_colorimetry(2, 0, 2, 2, false, 1080),
	       V4L2_COLORSPACE_REC709, V4L2_YCBCR_ENC_709,
	       V4L2_XFER_FUNC_709, V4L2_QUANTIZATION_DEFAULT);
	expect("YQ3", hdmirx_avi_colorimetry(2, 0, 2, 3, false, 1080),
	       V4L2_COLORSPACE_REC709, V4L2_YCBCR_ENC_709,
	       V4L2_XFER_FUNC_709, V4L2_QUANTIZATION_DEFAULT);

	/* A DVI source sends no AVI InfoFrame: full-range RGB. */
	expect("dvi", hdmirx_dvi_colorimetry(), V4L2_COLORSPACE_SRGB,
	       V4L2_YCBCR_ENC_DEFAULT, V4L2_XFER_FUNC_SRGB,
	       V4L2_QUANTIZATION_FULL_RANGE);

	if (failures) {
		printf("%d mismatched field(s)\n", failures);
		return 1;
	}

	return 0;
}
"""


def _added_lines(patch: Path) -> list[str]:
    return [
        line[1:]
        for line in patch.read_text().splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]


def _extract_pure_mapping(added: list[str]) -> str:
    """Lift the struct and the two pure functions out of the patch verbatim."""
    struct_open = added.index(STRUCT_OPEN)
    struct_close = added.index(STRUCT_CLOSE, struct_open) + 1

    map_body = added.index(MAP_SIGNATURE)
    if added[map_body - 1] != MAP_RETURN:
        raise AssertionError("mapping function signature moved")

    stop = next(
        i for i, line in enumerate(added) if line.startswith(AFTER_LAST_PURE_FN)
    )

    return "\n".join(added[struct_open:struct_close] + added[map_body - 1 : stop])


class AviColorimetryTableTests(unittest.TestCase):
    def test_every_table_row_including_fallbacks_and_dvi(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        extracted = _extract_pure_mapping(_added_lines(repo / PATCH))

        # Non-vacuity: a harness that lifted an empty or truncated function
        # would still compile a main() full of passing assertions.
        self.assertIn("hdmirx_dvi_colorimetry", extracted)
        self.assertIn("V4L2_COLORSPACE_DCI_P3", extracted)
        self.assertIn("V4L2_YCBCR_ENC_BT2020_CONST_LUM", extracted)
        self.assertGreater(len(extracted.splitlines()), 100)

        source = PREAMBLE + extracted + DRIVER
        with tempfile.TemporaryDirectory() as directory:
            c_file = Path(directory) / "colorimetry.c"
            binary = Path(directory) / "colorimetry"
            c_file.write_text(source)
            subprocess.run(
                ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                 str(c_file), "-o", str(binary)], check=True,
            )
            subprocess.run([str(binary)], check=True)
