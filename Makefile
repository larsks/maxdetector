PYFILES = \
	ifconfig.py \
	main.py \
	maxdetector.py \
	server.py

MPY_FILES = $(PYFILES:.py=.mpy)

FILES = \
	$(MPY_FILES) \
	ui.html \
	static/md.js \
	static/style.css \
	static/max.jpg

PYBOARD = pyboard
PYBOARD_DEVICE = /dev/ttyUSB0
PYBOARD_SPEED = 115200

%.mpy: %.py
	mpy-cross -o $@ $<

all: $(MPY_FILES)

upload: .lastupload

.lastupload: $(FILES)
	@set -e; \
	for file in $?; do \
		echo "upload $$file"; \
		$(PYBOARD) -d $(PYBOARD_DEVICE) -b $(PYBOARD_SPEED) \
			-f cp ./$$file $$file; \
	done
	touch $@
