"""RTP encoding profiles shared by broadcasts and physical speaker tests."""

CODECS = {
    "g722": {"encoder": "g722", "rate": 16000, "samples": 320, "payload": 9, "packet_size": 172},
    "pcma": {"encoder": "pcm_alaw", "rate": 8000, "samples": 160, "payload": 8, "packet_size": 172},
    "pcmu": {"encoder": "pcm_mulaw", "rate": 8000, "samples": 160, "payload": 0, "packet_size": 172},
    "opus": {"encoder": "libopus", "rate": 48000, "samples": 960, "payload": 111, "packet_size": 1200},
}
DEFAULT_CODEC = "g722"


def rtp_output_args(codec: str, endpoints: list[str], ssrc: int) -> list[str]:
    profile = CODECS[codec]
    args = [
        "-map", "0:a",
        "-af", f"aresample={profile['rate']}:async=1,asetnsamples=n={profile['samples']}",
        "-c:a", profile["encoder"], "-ar", str(profile["rate"]), "-ac", "1",
    ]
    if codec == "opus":
        args += ["-b:a", "64k", "-application", "voip", "-frame_duration", "20"]
    if len(endpoints) == 1:
        args += ["-payload_type", str(profile["payload"]), "-ssrc", str(ssrc), "-f", "rtp",
                 f"rtp://{endpoints[0]}?pkt_size={profile['packet_size']}"]
    else:
        slaves = [
            f"[select=a:f=rtp:ssrc={ssrc}:seq=0:payload_type={profile['payload']}]"
            f"rtp://{endpoint}?pkt_size={profile['packet_size']}"
            for endpoint in endpoints
        ]
        args += ["-f", "tee", "|".join(slaves)]
    return args
