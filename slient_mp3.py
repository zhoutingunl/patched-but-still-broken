from pydub import AudioSegment

duration = 2
silent = AudioSegment.silent(duration=duration*1000)
silent = silent.set_frame_rate(44100).set_channels(2).set_sample_width(2)
silent.export(f"slient_{duration}s.mp3", format="mp3")

