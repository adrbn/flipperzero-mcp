# TCP-UART Bridge for Flipper Zero WiFi Dev Board
# ESP-IDF project configuration

cmake_minimum_required(VERSION 3.16)

set(EXTRA_COMPONENT_DIRS "components")

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(tcp_uart_bridge)
