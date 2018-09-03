#!/usr/bin/env python3

import av
import av.filter
import os
import sys
import queue
from subprocess import Popen, PIPE
from threading import Thread
from time import sleep

currentdir = os.path.dirname(os.path.abspath(__file__))
parentdir = os.path.abspath(os.path.join(currentdir, os.pardir))
sys.path.insert(0, parentdir)

V_FIFO = queue.Queue(maxsize=100)


# main decoding thread
class Decode(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.input = [
            'test_clips/waves.mp4',
            'test_clips/test.mp4',
            'test_clips/water.mp4',
            'test_clips/test.mp4'
         ]
        self.w = 1024
        self.h = 576
        self.fps = 25

    def run(self):
        for input in self.input:
            container = av.open(input, 'r')

            graph = av.filter.Graph()
            fchain = []
            fchain.append(graph.add_buffer(
                width=self.w, height=self.h, format='rgb24'))
            fchain.append(graph.add('fps', '{}'.format(self.fps)))
            fchain[-2].link_to(fchain[-1])
            fchain.append(graph.add("buffersink"))
            fchain[-2].link_to(fchain[-1])

            for packet in container.demux():
                orig_fps = packet.stream.rate

                for frame in packet.decode():
                    type = packet.stream.type

                    if type == 'video':
                        new_v_frame = frame.reformat(self.w, self.h, 'rgb24')

                        if orig_fps != self.fps:
                            fchain[0].push(new_v_frame)
                            out_v_frame = fchain[-1].pull()
                        else:
                            out_v_frame = new_v_frame

                        out_v_frame.pts = None
                        V_FIFO.put(out_v_frame.planes[0])


dec = Decode()
dec.setDaemon(True)
dec.start()

sleep(1)

play = None

while not V_FIFO.empty():
    v = V_FIFO.get(block=True, timeout=0.7)
    if not play:
        cmd = [
            'ffplay',
            '-f', 'rawvideo',
            '-pixel_format', 'rgb24',
            '-video_size', '1024x576',
            '-i', '-',
            ]
        play = Popen(cmd, stdin=PIPE)
    try:
        play.stdin.write(v.to_bytes())
    except IOError as e:
        print(e)
        break

if play is not None:
    play.kill()
print("\ndone!")
