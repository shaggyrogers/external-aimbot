g++ windowcap_x11.cpp windowcap.cpp -std=c++17 -fPIC -shared -o windowcap.so `pkg-config --cflags --libs python3 opencv4 x11`
