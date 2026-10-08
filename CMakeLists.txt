cmake_minimum_required(VERSION 3.22)

#
# This file is generated only once,
# and is not re-generated if converter is called multiple times.
#
# User is free to modify the file as much as necessary
#

# Setup compiler settings
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)


# Define the build type
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE "Debug")
endif()

# Set the project name
set(CMAKE_PROJECT_NAME Hafta-01)

# Enable compile command to ease indexing with e.g. clangd
set(CMAKE_EXPORT_COMPILE_COMMANDS TRUE)

# Core project settings
project(${CMAKE_PROJECT_NAME})
message("Build type: " ${CMAKE_BUILD_TYPE})

# Enable CMake support for ASM and C languages
enable_language(C ASM)

# Create an executable object type
add_executable(${CMAKE_PROJECT_NAME})

# Add STM32CubeMX generated sources
add_subdirectory(cmake/stm32cubemx)

# Link directories setup
target_link_directories(${CMAKE_PROJECT_NAME} PRIVATE
    # Add user defined library search paths
)

# SEGGER SystemView (ST-Link + tools/sysview_stlink.py ile canli izleme)
# Kapatmak icin: cmake -DSYSVIEW=OFF ...
option(SYSVIEW "SEGGER SystemView kaydini derlemeye ekle" ON)
if(SYSVIEW)
    set(SEGGER_DIR ${CMAKE_CURRENT_SOURCE_DIR}/Middlewares/Third_Party/SEGGER)
    # Iz makrolari FreeRTOSConfig.h uzerinden FreeRTOS cekirdegine de girer,
    # bu yuzden ayarlar tum hedeflerin paylastigi stm32cubemx arayuzune eklenir.
    target_include_directories(stm32cubemx INTERFACE
        ${SEGGER_DIR}/Config
        ${SEGGER_DIR}/SEGGER
        ${SEGGER_DIR}/RTT
        ${SEGGER_DIR}/SYSVIEW
        ${SEGGER_DIR}/OS
    )
    target_compile_definitions(stm32cubemx INTERFACE USE_SYSVIEW=1)
    target_sources(${CMAKE_PROJECT_NAME} PRIVATE
        ${SEGGER_DIR}/RTT/SEGGER_RTT.c
        ${SEGGER_DIR}/SYSVIEW/SEGGER_SYSVIEW.c
        ${SEGGER_DIR}/OS/SEGGER_SYSVIEW_FreeRTOS.c
        ${SEGGER_DIR}/Config/SEGGER_SYSVIEW_Config_FreeRTOS.c
    )
endif()

# Add sources to executable
target_sources(${CMAKE_PROJECT_NAME} PRIVATE
    # Add user sources here
)

# Add include paths
target_include_directories(${CMAKE_PROJECT_NAME} PRIVATE
    # Add user defined include paths
)

# Add project symbols (macros)
target_compile_definitions(${CMAKE_PROJECT_NAME} PRIVATE
    # Add user defined symbols
)

# Remove wrong libob.a library dependency when using cpp files
list(REMOVE_ITEM CMAKE_C_IMPLICIT_LINK_LIBRARIES ob)

# Add linked libraries
target_link_libraries(${CMAKE_PROJECT_NAME}
    stm32cubemx

    # Add user defined libraries
)
