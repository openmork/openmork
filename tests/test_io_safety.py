from __future__ import annotations

import io

from core.agent_runtime.io_safety import SafeWriter


class _BrokenStream(io.StringIO):
    def write(self, s):
        raise OSError("broken pipe")

    def flush(self):
        raise OSError("broken pipe")


def test_safe_writer_handles_broken_pipe_write_and_flush():
    stream = _BrokenStream()
    writer = SafeWriter(stream)

    assert writer.write("abc") == 3
    writer.flush()  # no raise
    assert writer.isatty() is False
