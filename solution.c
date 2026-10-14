#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    uint32_t height;
    uint32_t width;
    uint16_t kernel_height;
    uint16_t kernel_width;
    size_t data_size;
    uint8_t *pixels;
    int8_t *kernel;
} InputData;

static int parse_arguments(int argc, char **argv,
                           const char **input_path, const char **output_path)
{
    for (int index = 1; index < argc; ++index) {
        if (strcmp(argv[index], "-i") != 0 &&
            strcmp(argv[index], "-o") != 0) {
            continue;
        }

        if (index + 1 >= argc || argv[index + 1][0] == '\0' ||
            strcmp(argv[index + 1], "-i") == 0 ||
            strcmp(argv[index + 1], "-o") == 0) {
            return 10;
        }

        if (strcmp(argv[index], "-i") == 0) {
            *input_path = argv[index + 1];
        } else {
            *output_path = argv[index + 1];
        }
        ++index;
    }

    return *input_path != NULL && *output_path != NULL ? EXIT_SUCCESS : 10;
}

static int read_input(const char *path, InputData *input)
{
    FILE *file = fopen(path, "rb");
    if (file == NULL) {
        perror(path);
        return EXIT_FAILURE;
    }

    int status = EXIT_FAILURE;
    if (fread(&input->height, sizeof input->height, 1, file) != 1 ||
        fread(&input->width, sizeof input->width, 1, file) != 1) {
        fputs("Cannot read matrix dimensions.\n", stderr);
        goto cleanup;
    }

    if (input->height != 0 && input->width != 0) {
        if (input->height > SIZE_MAX / input->width / 3) {
            fputs("Matrix data size is too large.\n", stderr);
            goto cleanup;
        }
        input->data_size = (size_t)input->height * input->width * 3;
        input->pixels = malloc(input->data_size);
        if (input->pixels == NULL) {
            fputs("Cannot allocate matrix data.\n", stderr);
            goto cleanup;
        }
        if (fread(input->pixels, 1, input->data_size, file) != input->data_size) {
            fputs("Cannot read matrix data.\n", stderr);
            goto cleanup;
        }
    }

    if (fread(&input->kernel_height, sizeof input->kernel_height, 1, file) != 1 ||
        fread(&input->kernel_width, sizeof input->kernel_width, 1, file) != 1) {
        fputs("Cannot read kernel dimensions.\n", stderr);
        goto cleanup;
    }
    if (input->kernel_height == 0 || input->kernel_width == 0 ||
        input->kernel_height % 2 == 0 || input->kernel_width % 2 == 0) {
        fputs("Kernel dimensions must be positive and odd.\n", stderr);
        goto cleanup;
    }
    if (input->kernel_height > SIZE_MAX / input->kernel_width) {
        fputs("Kernel data size is too large.\n", stderr);
        goto cleanup;
    }

    size_t kernel_size = (size_t)input->kernel_height * input->kernel_width;
    input->kernel = malloc(kernel_size);
    if (input->kernel == NULL) {
        fputs("Cannot allocate kernel data.\n", stderr);
        goto cleanup;
    }
    if (fread(input->kernel, 1, kernel_size, file) != kernel_size) {
        fputs("Cannot read kernel data.\n", stderr);
        goto cleanup;
    }
    status = EXIT_SUCCESS;

cleanup:
    if (fclose(file) != 0) {
        fputs("Cannot close input file.\n", stderr);
        status = EXIT_FAILURE;
    }
    return status;
}

static uint8_t normalize_sum(int64_t sum)
{
    if (sum > 255) {
        return (uint8_t)(sum % 251);
    }
    if (sum < 0) {
        return (uint8_t)((-sum) % 241);
    }
    return (uint8_t)sum;
}

static void convolve(const InputData *input, uint8_t *result)
{
    const size_t height = input->height;
    const size_t width = input->width;
    const size_t kernel_height = input->kernel_height;
    const size_t kernel_width = input->kernel_width;

    for (size_t row = 0; row < height; ++row) {
        const int64_t source_top = (int64_t)row - (int64_t)(kernel_height / 2);
        const size_t kernel_row_begin = source_top < 0 ? (size_t)(-source_top) : 0;
        size_t kernel_row_end = kernel_height;
        if ((int64_t)kernel_row_end > (int64_t)height - source_top) {
            kernel_row_end = (size_t)((int64_t)height - source_top);
        }

        for (size_t column = 0; column < width; ++column) {
            const int64_t source_left = (int64_t)column - (int64_t)(kernel_width / 2);
            const size_t kernel_column_begin =
                source_left < 0 ? (size_t)(-source_left) : 0;
            size_t kernel_column_end = kernel_width;
            if ((int64_t)kernel_column_end > (int64_t)width - source_left) {
                kernel_column_end = (size_t)((int64_t)width - source_left);
            }

            /* Even the largest supported kernel cannot overflow int64_t. */
            int64_t sum_a = 0;
            int64_t sum_b = 0;
            int64_t sum_c = 0;

            for (size_t kernel_row = kernel_row_begin;
                 kernel_row < kernel_row_end; ++kernel_row) {
                const size_t source_row = (size_t)(source_top + (int64_t)kernel_row);
                const size_t source_column =
                    (size_t)(source_left + (int64_t)kernel_column_begin);
                const uint8_t *pixel = input->pixels +
                    3 * (source_row * width + source_column);
                const int8_t *coefficient = input->kernel +
                    kernel_row * kernel_width + kernel_column_begin;

                for (size_t kernel_column = kernel_column_begin;
                     kernel_column < kernel_column_end; ++kernel_column) {
                    const int64_t weight = *coefficient++;
                    sum_a += weight * pixel[0];
                    sum_b += weight * pixel[1];
                    sum_c += weight * pixel[2];
                    pixel += 3;
                }
            }

            const size_t offset = 3 * (row * width + column);
            result[offset] = normalize_sum(sum_a);
            result[offset + 1] = normalize_sum(sum_b);
            result[offset + 2] = normalize_sum(sum_c);
        }
    }
}

static int write_output(const char *path, const InputData *input,
                        const uint8_t *result)
{
    FILE *file = fopen(path, "wb");
    if (file == NULL) {
        perror(path);
        return EXIT_FAILURE;
    }

    int status = EXIT_SUCCESS;
    if (fwrite(&input->height, sizeof input->height, 1, file) != 1 ||
        fwrite(&input->width, sizeof input->width, 1, file) != 1 ||
        (input->data_size != 0 &&
         fwrite(result, 1, input->data_size, file) != input->data_size)) {
        fputs("Cannot write output data.\n", stderr);
        status = EXIT_FAILURE;
    }
    if (fclose(file) != 0) {
        fputs("Cannot close output file: write error.\n", stderr);
        status = EXIT_FAILURE;
    }
    return status;
}

int main(int argc, char **argv)
{
    const char *input_path = NULL;
    const char *output_path = NULL;
    int status = parse_arguments(argc, argv, &input_path, &output_path);
    if (status != EXIT_SUCCESS) {
        fputs("Usage: solution -i input_file -o output_file\n", stderr);
        return status;
    }

    InputData input = {0};
    uint8_t *result = NULL;
    status = read_input(input_path, &input);
    if (status != EXIT_SUCCESS) {
        goto cleanup;
    }

    if (input.data_size != 0) {
        result = malloc(input.data_size);
        if (result == NULL) {
            fputs("Cannot allocate result data.\n", stderr);
            status = EXIT_FAILURE;
            goto cleanup;
        }
        convolve(&input, result);
    }
    status = write_output(output_path, &input, result);

cleanup:
    free(result);
    free(input.kernel);
    free(input.pixels);
    return status;
}
