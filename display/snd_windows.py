import sys
from cStringIO import StringIO
import puremixer
import wingame


class Sound:
    # Mono only
    has_sound = has_music = 0   # until initialized

    BUFFERTIME = 0.09
    FLOPTIME   = 0.07

    def __init__(self, freq=44100, bits=16):
        self.freq = int(freq)
        self.bits = int(bits)
        self.bufsize = (int(self.BUFFERTIME*self.freq*self.bits/8) + 64) & ~63

        try:
            self.audio = wingame.Audio(1, self.freq, self.bits, self.bufsize)
        except Exception, e:
            print >> sys.stderr, "sound disabled: %s: %s" % (
                e.__class__.__name__, e)
            return
        self.mixer = puremixer.PureMixer(self.freq, self.bits, self.bits==16,
                                         byteorder='little')
        self.mixer_channels = []
        self.mixer_accum = {}
        self.has_sound = 1
        self.has_music = 1

    def stop(self):
        self.audio.close()

    def sound(self, f):
        return self.mixer.wavesample(f.fopen())

    def flop(self):
        self.mixer_accum = {}
        while self.audio.ready():
            self.audio.write(self.mixer.mix(self.mixer_channels, self.bufsize))
        return self.FLOPTIME

    def play(self, sound, lvolume, rvolume):
        # volume ignored
        if sound not in self.mixer_accum:
            self.mixer_channels.append(StringIO(sound))
            self.mixer_accum[sound] = 1

    def play_musics(self, musics, loop_from):
        self.cmusics = musics, loop_from, -1
        self.mixer_channels.insert(0, self)

    def read(self, size):
        "Provide some more data to self.mixer.poll()."
        musics, loop_from, c = self.cmusics
        if c < 0:
            data = ''
        else:
            data = musics[c].mixed.decode(self.mixer, size)
        if not data:
            c += 1
            if c >= len(musics):  # end
                c = loop_from
                if c >= len(musics):
                    return ''
            self.cmusics = musics, loop_from, c
            try:
                mixed = musics[c].mixed
            except AttributeError:
                mixed = musics[c].mixed = Music(musics[c].freezefilename())
            mixed.openchannel()
            data = mixed.decode(self.mixer, size)
        if 0 < len(data) < size:
            data += self.read(size - len(data))
        return data

    def fadeout(self, millisec):
        self.cmusics = [], 0, -1


class Music:
    def __init__(self, filename):
        self.filename = filename
        self.w = None
        self.sampledata = StringIO()
    def openchannel(self):
        if self.w is None:
            import wave
            self.w = w = wave.open(open(self.filename, 'rb'), 'r')
            self.w_params = (w.getnchannels(),
                             w.getsampwidth(),
                             w.getframerate())
            chan, width, freq = self.w_params
            self.dataleft = w.getnframes() * (chan*width)
        self.sampledata.seek(0)
    def decode(self, mixer, bytecount):
        result = self.sampledata.read(bytecount)
        if not result and self.dataleft > 0:
            # decode and convert some more data
            chan, width, freq = self.w_params
            framecount = bytecount / (chan*width)
            inputdata = self.w.readframes(framecount)
            self.dataleft -= len(inputdata)
            result = mixer.resample(inputdata,
                                    freq = freq,
                                    bits = width * 8,
                                    signed = width > 1,
                                    channels = chan,
                                    byteorder = 'little')
            del inputdata
            self.sampledata.write(result)
            if len(result) > bytecount:
                self.sampledata.seek(bytecount-len(result), 1)
                result = result[:bytecount]
        return result


def htmloptionstext(nameval):
    import modes
    l = ['<font size=-1>Sampling <%s>' % nameval('select', 'bits')]
    for bits in (8, 16):
        l.append('<'+nameval('option', 'bits', str(bits), default='16')+'>'+
                 '%d bits' % bits)
    l+= ['</select> rate ',
         '<%s size=5>Hz</font>' % nameval('text', 'freq', default='44100'),
         '<br>',
         modes.musichtmloptiontext(nameval)]
    return '\n'.join(l)
