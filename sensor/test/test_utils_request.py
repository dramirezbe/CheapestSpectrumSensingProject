import json
import pytest
from unittest.mock import patch, MagicMock
from utils.request_util import RequestClient, ZmqPub, ZmqSub
import zmq
import zmq.asyncio
import asyncio


# =============================================================================
# RequestClient
# =============================================================================

@pytest.fixture
def mock_logger():
    return MagicMock()


@pytest.fixture
def client(mock_logger):
    return RequestClient("http://testserver", verbose=True, logger=mock_logger)


# ----------------------------------------------------------------------
# GET
# ----------------------------------------------------------------------

def test_requestclient_get_success(client):
    """GET request → success (2xx)."""
    mock_resp = MagicMock(status_code=200)

    with patch("requests.request", return_value=mock_resp) as mock_req:
        rc, resp = client.get("/ping")

    mock_req.assert_called_once()
    assert rc == 0
    assert resp is mock_resp


def test_requestclient_get_client_error(client):
    """GET request → client error (4xx)."""
    mock_resp = MagicMock(status_code=404)

    with patch("requests.request", return_value=mock_resp):
        rc, resp = client.get("/missing")

    assert rc == 1
    assert resp.status_code == 404


# ----------------------------------------------------------------------
# POST JSON
# ----------------------------------------------------------------------

def test_requestclient_post_json_success(client):
    mock_resp = MagicMock(status_code=201)

    with patch("requests.request", return_value=mock_resp) as mock_req:
        rc, resp = client.post_json("/submit", {"a": 1})

    mock_req.assert_called_once()
    assert rc == 0
    assert resp is mock_resp


def test_requestclient_post_json_bad_json(client):
    """Force JSON serialization error."""
    bad_obj = { "x": set([1, 2, 3]) }  # sets no son JSON serializables

    rc, resp = client.post_json("/bad", bad_obj)

    assert rc == 2
    assert resp is None
    client._log.error.assert_called_once()


# ----------------------------------------------------------------------
# Exceptions in requests.request
# ----------------------------------------------------------------------

def test_requestclient_timeout(client):
    with patch("requests.request", side_effect=Exception("timeout")):
        rc, resp = client.get("/test")
        assert rc in (1, 2)  # depende de tipo de excepción
        assert resp is None


@patch("requests.request", side_effect=Exception("unexpected"))
def test_requestclient_unexpected_error(mock_req, client):
    rc, resp = client.get("/boom")
    assert rc == 2
    assert resp is None


# =============================================================================
# ZmqPub & ZmqSub (using inproc transport)
# =============================================================================

@pytest.mark.asyncio
async def test_zmq_pub_sub_basic():
    """
    Test real ZMQ pub/sub using inproc:// to avoid filesystem sockets.
    """
    addr = "inproc://test"
    topic = "demo"

    # Publisher
    pub = ZmqPub(addr)

    # Subscriber
    sub = ZmqSub(addr, topic)

    # Give ZeroMQ time to connect
    await asyncio.sleep(0.05)

    payload = {"x": 42}
    pub.public_client(topic, payload)

    # Subscriber waits for one message
    msg = await asyncio.wait_for(sub.wait_msg(), timeout=1.0)

    assert msg == payload

    pub.close()
    sub.close()


@pytest.mark.asyncio
async def test_zmq_sub_filters_other_topics():
    addr = "inproc://test2"
    topic = "A"

    pub = ZmqPub(addr)
    sub = ZmqSub(addr, topic)

    await asyncio.sleep(0.05)

    # Send different topic → must be ignored
    pub.public_client("B", {"ignore": True})

    # Send correct topic → must be received
    pub.public_client("A", {"ok": True})

    msg = await asyncio.wait_for(sub.wait_msg(), timeout=1.0)

    assert msg == {"ok": True}

    pub.close()
    sub.close()
