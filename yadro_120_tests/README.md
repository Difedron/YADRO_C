# 120 дополнительных тестов для YADRO C17

Набор построен строго по формату ТЗ: A/B/C interleaved, D signed int8, zero-padding, ядро без переворота, нормализация `%251`/`%241`.

## Состав

- 98 валидных бинарных тестов с эталонными `.out`;
- 14 тестов битого/усечённого ввода и невалидных размеров ядра;
- 8 тестов CLI/путей (`return 10`, отсутствующие файлы, имя с `-`, input==output).

## Запуск

```bash
gcc -std=c17 -O2 -Wall -Wextra -Wpedantic solution.c -o solution
python3 yadro_120_tests/run_120_tests.py ./solution
```

Ожидаемый итог: `Passed 120/120 tests`. Каждый тест имеет таймаут 60 секунд.

## Важно

Тесты 108-111 (нулевые/чётные размеры D) и другие malformed-input cases выходят за гарантии валидного входа из ТЗ и проверяют только устойчивость/качество кода. Нулевые H/W тоже не оговорены ТЗ напрямую, но проверяются как защитный edge case.

Практический runtime-тест, который гарантированно переполняет 32-битный accumulator, намеренно не включён: для прямой свёртки он требует порядка миллиардов операций. Безопасность `int64_t` проверяется математической оценкой отдельно: `65535² * 255 * 128 = 140183454384000 < INT64_MAX`.

## Категории

- 001_scalar_zero: 1x1, zero pixel, identity kernel
- 002_scalar_255: 1x1, all channels 255, identity kernel
- 003_scalar_negative: 1x1, signed -1 kernel
- 004_scalar_min_coeff: 1x1, D=-128
- 005_scalar_max_coeff: 1x1, D=127
- 006_scalar_zero_kernel: 1x1, D=0
- 007_zero_both_dims: H=0,W=0, valid kernel still present
- 008_zero_height: H=0,W=5, 3x3 kernel
- 009_zero_width: H=5,W=0, 1x3 kernel
- 010_one_by_two: 1x2 identity
- 011_two_by_one: 2x1 identity
- 012_one_by_five: 1x5 identity ramp
- 013_five_by_one: 5x1 identity ramp
- 014_two_by_two: 2x2 identity
- 015_three_by_three: 3x3 identity
- 016_rect_identity: 4x7 identity, varied channels
- 017_mixed_channels: 2x3 independent A/B/C
- 018_all_max: 3x2 all 255
- 019_checker: 3x4 checkerboard channels
- 020_channel_ramps: 7x6 three distinct ramps
- 021_1x1_k3: 1x1 with 3x3 kernel, only center contributes
- 022_1x1_k5_asym: 1x1 with asymmetric 5x5 kernel
- 023_row_k1x3: 1x4 with 1x3 kernel
- 024_row_kernel_larger: 1x4 with 1x7 kernel larger than row
- 025_col_k3x1: 4x1 with 3x1 kernel
- 026_col_kernel_larger: 4x1 with 7x1 kernel larger than column
- 027_2x2_k3: 2x2 with 3x3 all-ones padding
- 028_2x3_k5x3: kernel taller than image
- 029_3x2_k3x5: kernel wider than image
- 030_3x3_k5: 5x5 kernel larger both ways
- 031_kernel_impulse_tl: 3x3 kernel impulse tl; detects accidental flip
- 032_kernel_impulse_tr: 3x3 kernel impulse tr; detects accidental flip
- 033_kernel_impulse_bl: 3x3 kernel impulse bl; detects accidental flip
- 034_kernel_impulse_br: 3x3 kernel impulse br; detects accidental flip
- 035_asym_k3x3: asymmetric 3x3 signed kernel
- 036_asym_k3x5: asymmetric 3x5 kernel
- 037_asym_k5x3: asymmetric 5x3 kernel
- 038_row_asym: 1x7 asymmetric 1x5
- 039_col_asym: 7x1 asymmetric 5x1
- 040_image_impulse_corner: input impulse at top-left, 3x3 kernel
- 041_image_impulse_center: input impulse at center, no-flip detector
- 042_top_edge_signal: nonzero top edge exercises vertical padding
- 043_left_edge_signal: nonzero left edge exercises horizontal padding
- 044_kernel_7x9_gt_image: 7x9 kernel on 3x4 image
- 045_kernel_11x13_gt_2x2: 11x13 kernel on 2x2 image
- 046_sum_0: exact scalar arithmetic boundary: sum_0
- 047_sum_1: exact scalar arithmetic boundary: sum_1
- 048_sum_240: exact scalar arithmetic boundary: sum_240
- 049_sum_241: exact scalar arithmetic boundary: sum_241
- 050_sum_250: exact scalar arithmetic boundary: sum_250
- 051_sum_251: exact scalar arithmetic boundary: sum_251
- 052_sum_255: exact scalar arithmetic boundary: sum_255
- 053_sum_neg1: exact scalar arithmetic boundary: sum_neg1
- 054_sum_neg240: exact scalar arithmetic boundary: sum_neg240
- 055_sum_neg241: exact scalar arithmetic boundary: sum_neg241
- 056_sum_neg242: exact scalar arithmetic boundary: sum_neg242
- 057_sum_256: two positive contributions can cross 255 to exactly 256
- 058_sum_257: exact 257 at left output
- 059_sum_501: 250+251 positive accumulation
- 060_sum_502_mod0: 502 % 251 == 0
- 061_sum_503_mod1: 503 % 251 == 1
- 062_neg482_mod0: -482 => 482 % 241 == 0
- 063_neg483_mod1: -483 => 483 % 241 == 1
- 064_max_positive_product: 255*127 single-product extreme
- 065_max_negative_product: 255*(-128) single-product extreme
- 066_cancel_zero: 100-200+100 = 0 at center
- 067_cancel_plus1: 100-199+100 = 1
- 068_cancel_minus1: 100-201+100 = -1
- 069_extreme_coeff_mix: kernel includes both -128 and 127
- 070_all255_all127: 3x3 all-255 image, all +127 kernel
- 071_all255_allneg128: 3x3 all-255 image, all -128 kernel
- 072_alternating_kernel_signs: alternating signed kernel
- 073_alternating_pixels: 0/255 alternating pixels with signed kernel
- 074_channels_different_signs: same position yields positive/negative/zero-ish channel sums
- 075_channels_different_modulo: three channels deliberately cross modulo rules differently
- 076_random_4x6_k1x5: fixed-seed differential random case 1; full signed coefficient range
- 077_random_5x1_k3x1: fixed-seed differential random case 2; full signed coefficient range
- 078_random_7x3_k5x7: fixed-seed differential random case 3; full signed coefficient range
- 079_random_7x8_k3x9: fixed-seed differential random case 4; full signed coefficient range
- 080_random_5x2_k3x9: fixed-seed differential random case 5; full signed coefficient range
- 081_random_6x8_k5x3: fixed-seed differential random case 6; full signed coefficient range
- 082_random_4x6_k3x3: fixed-seed differential random case 7; full signed coefficient range
- 083_random_3x6_k7x3: fixed-seed differential random case 8; full signed coefficient range
- 084_random_3x5_k3x3: fixed-seed differential random case 9; full signed coefficient range
- 085_random_4x4_k3x5: fixed-seed differential random case 10; full signed coefficient range
- 086_random_7x8_k5x9: fixed-seed differential random case 11; full signed coefficient range
- 087_random_7x3_k5x1: fixed-seed differential random case 12; full signed coefficient range
- 088_random_7x1_k7x3: fixed-seed differential random case 13; full signed coefficient range
- 089_random_7x5_k1x1: fixed-seed differential random case 14; full signed coefficient range
- 090_random_4x4_k1x1: fixed-seed differential random case 15; full signed coefficient range
- 091_random_5x2_k1x7: fixed-seed differential random case 16; full signed coefficient range
- 092_random_1x2_k9x9: fixed-seed differential random case 17; full signed coefficient range
- 093_random_6x8_k1x9: fixed-seed differential random case 18; full signed coefficient range
- 094_random_6x2_k9x7: fixed-seed differential random case 19; full signed coefficient range
- 095_random_3x9_k3x3: fixed-seed differential random case 20; full signed coefficient range
- 096_random_4x2_k3x1: fixed-seed differential random case 21; full signed coefficient range
- 097_random_8x4_k9x9: fixed-seed differential random case 22; full signed coefficient range
- 098_random_4x1_k7x9: fixed-seed differential random case 23; full signed coefficient range
- 099_empty_file: empty file: cannot read H
- 100_truncated_H: only 1 byte of H
- 101_only_H: H present, W missing
- 102_truncated_W: H plus only 2 bytes of W
- 103_truncated_pixels_1x1: H=W=1 but only 2/3 ABC bytes
- 104_truncated_pixels_2x2: 2x2 ABC block one byte short
- 105_missing_DH: matrix complete, DH absent
- 106_missing_DW: DH present, DW absent
- 107_truncated_D: 3x3 D one byte short
- 108_zero_DH: DH=0 should be rejected
- 109_zero_DW: DW=0 should be rejected
- 110_even_DH: even DH should be rejected
- 111_even_DW: even DW should be rejected
- 112_size_overflow: H=W=UINT32_MAX triggers 3*H*W size overflow on 64-bit
- 113_cli_no_args: no arguments => 10
- 114_cli_only_i: only -i with valid filename => 10
- 115_cli_only_o: only -o with filename => 10
- 116_cli_flag_as_name: -i immediately followed by -o => 10
- 117_missing_input_path: both flags but input file does not exist => EXIT_FAILURE
- 118_missing_output_dir: output parent directory does not exist => EXIT_FAILURE
- 119_leading_dash_filenames: filenames beginning with '-' but not equal to flags are accepted
- 120_same_input_output: input and output may be same path because output opens after read/compute
