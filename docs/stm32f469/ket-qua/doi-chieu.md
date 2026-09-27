# Đối chiếu firmware ↔ tài liệu

Sinh tự động bởi `tools/doi_chieu_stm32.py`. Bộ này **không có sẵn đáp án**: nó đọc tài liệu trong kho của dự án rồi so với mã nguồn.


## Tài liệu văn bản đã nạp (3)

- `CMSIS-STM32F469XX-H` · `stm32f469xx.h` · 20285 dòng
- `PROE-STM32F469` · `proe_stm32f469.txt` · 1576 dòng
- `BSP-STM32469I-DISCO-H` · `stm32469i_discovery.h` · 362 dòng

## Chân LED

| LED | Tài liệu nói | Nguồn | Có trong firmware? |
|---|---|---|---|
| LED1 | `PG6` | `BSP-STM32469I-DISCO-H` (stm32469i_discovery.h) | **có** |
| LED2 | `PD4` | `BSP-STM32469I-DISCO-H` (stm32469i_discovery.h) | không |
| LED3 | `PD5` | `BSP-STM32469I-DISCO-H` (stm32469i_discovery.h) | không |
| LED4 | `PK3` | `BSP-STM32469I-DISCO-H` (stm32469i_discovery.h) | không |

## Fact trong kho (1)

| Chủ đề | Khoá | Giá trị | Tầng | Trích dẫn |
|---|---|---|---|---|
| `chip:STM32F469NI` | flash.size | 7.0 | BAC | CMSIS-STM32F469XX-H · dòng 1241–1280 |

## Biên dịch

- **dat**: `True`
- **cong_cu**: `arm-none-eabi-gcc`
- **so_loi**: `0`
- **so_canh_bao**: `0`
- **tep_ra**: `.eide/build/mach.elf`
- **tep_bin**: `.eide/build/mach.bin`
- **thieu_libc**: `True`
- **flash**: `224`
- **sram**: `0`
- **flash_toi_da**: `70`
- **sram_toi_da**: `0`
- **ty_le_flash**: `3.2`
- **ty_le_sram**: `None`
- **vi_sao_khong_dat**: ``

## Nạp vào bo

*Chưa có.*

## Log từ bo

*Chưa có.*
