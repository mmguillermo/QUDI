import matlab.engine
eng = matlab.engine.start_matlab()
print(eng.sin(2.0))
