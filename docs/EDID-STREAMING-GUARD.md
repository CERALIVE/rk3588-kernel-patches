# HDMI-RX streaming EDID guard [EXISTS]

Member `0040` rejects `VIDIOC_S_EDID` with `-EBUSY` while
`vb2_is_streaming(&stream->buf_queue)` is true. The guard precedes validation,
HPD changes, IRQ masking, EDID writes, and zero-block clearing. The ioctl and
vb2 queue share `stream->vlock`; no new lock or userspace-state dependency is
needed. Allocated but non-streaming buffers do not block EDID changes.

## Deferred board gate

Not executed here. Use the HDMI-RX node discovered on the board, not a fixed
video index, and retain a known-good EDID for restoration.

1. With capture stopped, read all EDID blocks with `VIDIOC_G_EDID` into a
   baseline byte buffer. Write a different valid EDID with `VIDIOC_S_EDID`;
   expect success. Read back and compare every byte with the requested EDID.
2. Start capture with allocated and queued buffers and successful `STREAMON`.
   From a second fd, issue `VIDIOC_S_EDID` with the baseline EDID. Expect
   return `-1`, `errno == EBUSY`. Read back all blocks and verify both the
   block count and bytes are unchanged from step 1.
3. While still streaming, issue a zero-block `VIDIOC_S_EDID`. Expect the same
   error and unchanged readback; clearing is renegotiation too.
4. Issue `STREAMOFF` without freeing the buffers. Repeat the baseline write;
   expect success and exact readback. Verify capture can restart normally.
5. Release buffers and close capture, then test an idle zero-block clear and
   restore the baseline. Record the clear and restore results separately.

`v4l2-ctl --set-edid` exercises the same ioctl; its error output should report
Device or resource busy during step 2. Use a syscall trace or a small ioctl
probe to record the exact errno rather than relying on its process exit code.
Record kernel/series SHA, node, raw EDID buffers, ioctl results, and capture
continuity. No hardware outcome is inferred from patch application.
