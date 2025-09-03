# src/agents/dbtools_client.py
import requests
import threading
import queue
import time
import json
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

BASE_URL = "http://127.0.0.1:8001/mcp"  # adjust if needed


class MCPStreamClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session_id: Optional[str] = None
        self._sse_resp: Optional[requests.Response] = None
        self._sse_thread: Optional[threading.Thread] = None
        self._events = queue.Queue()
        self._stop = threading.Event()

    def open_event_stream(self):
        log.info("Opening SSE stream...")
        resp = self.session.get(
            self.base_url,
            headers={"Accept": "text/event-stream"},
            stream=True,
            timeout=30,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"SSE open failed: {resp.status_code} {resp.text}")

        session_id = resp.headers.get("Mcp-Session-Id")
        if not session_id:
            raise RuntimeError("Server did not return Mcp-Session-Id on SSE open")
        self.session_id = session_id
        self._sse_resp = resp

        def _reader():
            try:
                for line in resp.iter_lines(decode_unicode=True):
                    if self._stop.is_set():
                        break
                    if not line:
                        continue
                    # Basic SSE format: lines like "data: <json>"
                    if line.startswith("data:"):
                        data = line[5:].strip()
                        self._events.put(("data", data))
                    else:
                        self._events.put(("raw", line))
            except Exception as e:
                self._events.put(("error", str(e)))

        self._sse_thread = threading.Thread(target=_reader, daemon=True)
        self._sse_thread.start()
        log.info("SSE stream opened. Mcp-Session-Id=%s", self.session_id)

    def post_jsonrpc(self, method: str, params: dict | None = None, rid: str = "1"):
        if not self.session_id:
            raise RuntimeError("No Mcp-Session-Id. Call open_event_stream() first.")
        payload = {
            "jsonrpc": "2.0",
            "id": rid,
            "method": method,
            "params": params or {},
        }
        headers = {
            "Content-Type": "application/json",
            # Many servers require client to accept both JSON and SSE
            "Accept": "application/json, text/event-stream",
            "Mcp-Session-Id": self.session_id,
        }
        log.info("POST %s %s", method, payload)
        resp = self.session.post(self.base_url, headers=headers, json=payload, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"JSON-RPC call failed: {resp.status_code} {resp.text}")
        return resp.json()

    def close(self):
        self._stop.set()
        try:
            if self._sse_resp is not None:
                self._sse_resp.close()
        finally:
            if self._sse_thread is not None:
                self._sse_thread.join(timeout=2)


def main():
    client = MCPStreamClient(BASE_URL)
    try:
        # 1) Open SSE first and capture Mcp-Session-Id
        client.open_event_stream()

        # 2) List tools: MCP JSON-RPC method is usually "tools/list"
        #    (Some stacks use "listTools"; your server should document it.
        #     Try "tools/list" first.)
        try:
            result = client.post_jsonrpc("tools/list", {})
        except RuntimeError as e:
            # If your implementation uses camelCase:
            log.warning("tools/list failed, trying listTools. Err=%s", e)
            result = client.post_jsonrpc("listTools", {})

        print("=== JSON-RPC Response ===")
        print(json.dumps(result, indent=2))

        # 3) Optionally read a couple SSE messages (if server emits notifications)
        time.sleep(0.5)
        drained = []
        while True:
            try:
                kind, data = client._events.get_nowait()
                drained.append((kind, data))
            except queue.Empty:
                break

        if drained:
            print("\n=== SSE Events (sample) ===")
            for kind, data in drained[:10]:
                # Pretty print data fields if JSON
                if kind == "data":
                    try:
                        obj = json.loads(data)
                        print("data:", json.dumps(obj, indent=2))
                    except json.JSONDecodeError:
                        print("data:", data)
                else:
                    print(kind + ":", data)

    finally:
        client.close()


if __name__ == "__main__":
    main()
