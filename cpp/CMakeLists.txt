cmake_minimum_required(VERSION 3.18)
project(fast_indicators LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Prefer modern FindPython with newer CMake.
set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 CONFIG REQUIRED)

# This CMakeLists.txt lives in cpp/, so sources are relative to cpp/.
pybind11_add_module(_fast_indicators indicators.cpp)