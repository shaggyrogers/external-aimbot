g++ windowcap_src/windowcap_x11.cpp windowcap_src/windowcap.cpp \
    -std=c++17 \
    -fPIC \
    -shared \
    -o windowcap.so \
    `pkg-config --cflags --libs python3 opencv4 x11`
