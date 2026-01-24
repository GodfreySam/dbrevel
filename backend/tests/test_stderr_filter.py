"""
Unit tests for MongoDB background error suppression.

Verifies that _StderrFilter suppresses MongoDB background reconnection tracebacks
while passing through all other stderr output (real errors still appear).
"""

import io

from app.main import _StderrFilter


def test_stderr_filter_suppresses_mongodb_autoreconnect_traceback():
    """MongoDB AutoReconnect traceback is suppressed (not written to stderr)."""
    sink = io.StringIO()
    flt = _StderrFilter(sink)
    traceback = """Traceback (most recent call last):
  File ".../pymongo/synchronous/mongo_client.py", line 123, in _process_periodic_tasks
    ...
  File ".../pymongo/synchronous/pool.py", line 456, in update_pool
    ...
pymongo.errors.AutoReconnect: connection closed
"""
    flt.write(traceback)
    flt.flush()
    assert sink.getvalue() == ""


def test_stderr_filter_suppresses_mongodb_gaierror_traceback():
    """MongoDB gaierror (DNS) traceback with 'nodename nor servname' is suppressed."""
    sink = io.StringIO()
    flt = _StderrFilter(sink)
    traceback = """Traceback (most recent call last):
  File ".../pymongo/synchronous/mongo_client.py", line 99, in _process_periodic_tasks
    ...
  File ".../pymongo/synchronous/pool.py", line 100, in remove_stale_sockets
    ...
socket.gaierror: [Errno 8] nodename nor servname provided, or not known
"""
    flt.write(traceback)
    flt.flush()
    assert sink.getvalue() == ""


def test_stderr_filter_suppresses_mongodb_pymongo_synchronous_path():
    """Traceback with pymongo/synchronous/ path is detected and suppressed."""
    sink = io.StringIO()
    flt = _StderrFilter(sink)
    traceback = """Traceback (most recent call last):
  File ".../pymongo/synchronous/mongo_client.py", line 1, in _process_periodic_tasks
    pass
pymongo.errors.ServerSelectionTimeoutError: timed out
"""
    flt.write(traceback)
    flt.flush()
    assert sink.getvalue() == ""


def test_stderr_filter_passes_through_real_errors():
    """Non-MongoDB stderr output is passed through (real errors still appear)."""
    sink = io.StringIO()
    flt = _StderrFilter(sink)
    flt.write("ValueError: something went wrong\n")
    flt.flush()
    assert "ValueError: something went wrong" in sink.getvalue()


def test_stderr_filter_passes_through_generic_traceback():
    """Generic Python traceback (not MongoDB) is passed through."""
    sink = io.StringIO()
    flt = _StderrFilter(sink)
    traceback = """Traceback (most recent call last):
  File "app/foo.py", line 10, in bar
    raise RuntimeError("oops")
RuntimeError: oops
"""
    flt.write(traceback)
    flt.flush()
    assert "RuntimeError: oops" in sink.getvalue()
    assert "app/foo.py" in sink.getvalue()


def test_stderr_filter_empty_write_no_op():
    """Empty write is a no-op."""
    sink = io.StringIO()
    flt = _StderrFilter(sink)
    flt.write("")
    flt.flush()
    assert sink.getvalue() == ""
