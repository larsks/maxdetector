PYFILES = \
	ifconfig.py \
	main.py \
	maxdetector.py \
	server.py

MPY_FILES = $(PYFILES:.py=.mpy)

%.mpy: %.py
	mpy-cross -o $@ $<

all: $(MPY_FILES)
