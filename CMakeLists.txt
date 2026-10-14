cmake_minimum_required(VERSION 3.20)

project(yadro_test C)

set(CMAKE_C_STANDARD 17)
set(CMAKE_C_STANDARD_REQUIRED ON)

add_executable(solution solution.c)

target_compile_options(solution PRIVATE
        -Wall
        -Wextra
        -Wpedantic
)

if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    target_compile_options(solution PRIVATE
            -fsanitize=address,undefined
            -fno-omit-frame-pointer
    )

    target_link_options(solution PRIVATE
            -fsanitize=address,undefined
    )
endif()