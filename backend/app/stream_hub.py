"""Hub distribusi audio live ke PC client (Windows Node) lewat HTTP stream.

Satu proses FFmpeg menghasilkan audio mentah G.711 A-law 8kHz mono. Chunk dibaca oleh engine
lalu dibagikan ke semua client yang sedang tersambung dan termasuk target siaran.
Client yang tidak termasuk target tetap tersambung tetapi tidak menerima data.
"""
import asyncio
import threading
from typing import Dict, Optional, Set, Tuple


class StreamHub:
    def __init__(self):
        self._lock = threading.Lock()
        # token -> (node_id, loop, asyncio.Queue)
        self._subs: Dict[object, Tuple[str, asyncio.AbstractEventLoop, asyncio.Queue]] = {}
        self._active = False
        self._target_all = False
        self._target_nodes: Set[str] = set()

    # --- Sisi client (dipanggil dari endpoint async) ---
    def subscribe(self, node_id: str, loop: asyncio.AbstractEventLoop):
        q: asyncio.Queue = asyncio.Queue(maxsize=400)  # ~8 detik audio (400 x 20ms)
        token = object()
        with self._lock:
            # Bersihkan koneksi lama yang stale untuk node_id yang sama
            stale_tokens = [tok for tok, (nid, _, _) in self._subs.items() if nid == node_id]
            for tok in stale_tokens:
                self._subs.pop(tok, None)
            self._subs[token] = (node_id, loop, q)
        return token, q

    def unsubscribe(self, token):
        with self._lock:
            self._subs.pop(token, None)

    def subscriber_ids(self):
        with self._lock:
            return [nid for nid, _, _ in self._subs.values()]

    # --- Sisi engine (dipanggil dari thread biasa) ---
    def begin(self, all_nodes: bool = False, nodes: Optional[Set[str]] = None):
        with self._lock:
            if all_nodes:
                subs = [(loop, q) for _, loop, q in self._subs.values()]
            elif nodes:
                target_set = set(nodes)
                subs = [
                    (loop, q) for nid, loop, q in self._subs.values()
                    if nid in target_set
                ]
            else:
                subs = []
        for loop, q in subs:
            self._call(loop, self._flush, q)

    def end(self, all_nodes: bool = False, nodes: Optional[Set[str]] = None):
        with self._lock:
            if all_nodes or nodes is None:
                subs = [(loop, q) for _, loop, q in self._subs.values()]
            elif nodes:
                target_set = set(nodes)
                subs = [
                    (loop, q) for nid, loop, q in self._subs.values()
                    if nid in target_set
                ]
            else:
                subs = []
        for loop, q in subs:
            self._call(loop, self._end_sub, q)

    def publish(self, chunk: bytes, all_nodes: bool = False, nodes: Optional[Set[str]] = None):
        with self._lock:
            if all_nodes:
                targets = [(loop, q) for _, loop, q in self._subs.values()]
            elif nodes:
                target_set = set(nodes)
                targets = [
                    (loop, q) for nid, loop, q in self._subs.values()
                    if nid in target_set
                ]
            else:
                targets = []
        for loop, q in targets:
            self._call(loop, self._put, q, chunk)

    def publish_event(self, event_dict: dict, all_nodes: bool = False, nodes: Optional[Set[str]] = None):
        import json
        payload = ("JSON:" + json.dumps(event_dict)).encode("utf-8")
        self.publish(payload, all_nodes=all_nodes, nodes=nodes)

    # --- internal ---
    @staticmethod
    def _call(loop, fn, *args):
        try:
            loop.call_soon_threadsafe(fn, *args)
        except RuntimeError:
            pass  # event loop sudah tertutup

    @staticmethod
    def _put(q: asyncio.Queue, chunk: bytes):
        if q.full():
            try:
                item = q.get_nowait()
                # Jangan pernah membuang pesan kontrol JSON
                if item.startswith(b"JSON:"):
                    q.put_nowait(item)
            except asyncio.QueueEmpty:
                pass
        try:
            q.put_nowait(chunk)
        except asyncio.QueueFull:
            pass

    @staticmethod
    def _end_sub(q: asyncio.Queue):
        # Buang hanya chunk audio mentah yang tersisa, TETAP pertahankan event JSON
        saved_events = []
        while not q.empty():
            try:
                item = q.get_nowait()
                if item.startswith(b"JSON:"):
                    saved_events.append(item)
            except asyncio.QueueEmpty:
                break
        for ev in saved_events:
            q.put_nowait(ev)
        q.put_nowait(b"STREAM_END")

    @staticmethod
    def _flush(q: asyncio.Queue):
        # Buang hanya chunk audio mentah, TETAP pertahankan event JSON
        saved_events = []
        while not q.empty():
            try:
                item = q.get_nowait()
                if item.startswith(b"JSON:"):
                    saved_events.append(item)
            except asyncio.QueueEmpty:
                break
        for ev in saved_events:
            q.put_nowait(ev)


stream_hub = StreamHub()
