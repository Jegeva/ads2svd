MAKEFLAGS += --jobs=$(shell nproc)
IN_DIR=in/Cores
OUT_DIR=out
IN_FILES=$(wildcard $(IN_DIR)/*.xml)
OUT_FILES=$(IN_FILES:$(IN_DIR)/%.xml=$(OUT_DIR)/%.svd)
INTER_FILES=$(IN_FILES:$(IN_DIR)/%.xml=$(OUT_DIR)/%.xml)

SAXONHE_PATH=/usr/share/java/Saxon-HE-9.9.1.5.jar

XLST_FILE=./ads2svd.xslt

#$(info OUTFILES   $(OUT_FILES) )

.PHONY: clean all 
.SECONDARY: $(INTER_FILES)

all: $(OUT_DIR) $(OUT_FILES)

$(OUT_DIR)/%.xml : $(IN_DIR)/%.xml
	./ads2svd.py -c ./in -i $<		

$(OUT_DIR)/%.svd : $(OUT_DIR)/%.xml $(XLST_FILE)
	java -jar $(SAXONHE_PATH) -xsl:$(XLST_FILE) -s:$< -o:$@

clean:
	rm out/*
