import socket
import subprocess
import unittest
from app.audio_codecs import CODECS, rtp_output_args


class CodecTests(unittest.TestCase):
    def test_unknown_codec_rejected(self):
        with self.assertRaises(KeyError):
            rtp_output_args('unknown', ['127.0.0.1:5004'], 1234)

    def test_rtp_packets_for_every_codec_and_fanout(self):
        for codec, profile in CODECS.items():
            for count in (1, 2):
                with self.subTest(codec=codec, destinations=count):
                    receivers = [socket.socket(socket.AF_INET, socket.SOCK_DGRAM) for _ in range(count)]
                    try:
                        for receiver in receivers:
                            receiver.bind(('127.0.0.1', 0))
                            receiver.settimeout(2)
                        endpoints = [f'127.0.0.1:{receiver.getsockname()[1]}' for receiver in receivers]
                        command = ['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                                   'sine=frequency=440:sample_rate=48000', '-t', '0.1',
                                   *rtp_output_args(codec, endpoints, 1234)]
                        result = subprocess.run(command, capture_output=True, timeout=10)
                        self.assertEqual(result.returncode, 0, result.stderr.decode())
                        for receiver in receivers:
                            packet = receiver.recv(2048)
                            self.assertEqual(packet[0] >> 6, 2)
                            self.assertEqual(packet[1] & 127, profile['payload'])
                            self.assertEqual(int.from_bytes(packet[8:12], 'big'), 1234)
                    finally:
                        for receiver in receivers:
                            receiver.close()


if __name__ == '__main__':
    unittest.main()
