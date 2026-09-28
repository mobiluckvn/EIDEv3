# Đối chiếu firmware ↔ tài liệu

Sinh tự động bởi `tools/doi_chieu_stm32.py`. Bộ này **không có sẵn đáp án**: nó đọc tài liệu trong kho của dự án rồi so với mã nguồn.


## Tài liệu văn bản đã nạp (4)

- `BSP-STM32469I-DISCO-C` · `stm32469i_discovery.c` · 943 dòng
- `CMSIS-STM32F469XX-H` · `stm32f469xx.h` · 20285 dòng
- `PROE-STM32F469` · `proe_stm32f469.txt` · 1576 dòng
- `BSP-STM32469I-DISCO-H` · `stm32469i_discovery.h` · 362 dòng

## Chân LED

| LED | Tài liệu nói | Nguồn | Có trong firmware? |
|---|---|---|---|
| LED1 | `PG6` | `BSP-STM32469I-DISCO-H` (stm32469i_discovery.h) | **có** |
| LED2 | `PD4` | `BSP-STM32469I-DISCO-H` (stm32469i_discovery.h) | **có** |
| LED3 | `PD5` | `BSP-STM32469I-DISCO-H` (stm32469i_discovery.h) | **có** |
| LED4 | `PK3` | `BSP-STM32469I-DISCO-H` (stm32469i_discovery.h) | **có** |

Chân có trong firmware mà tài liệu (phần LED) không nhắc tới: `PA0` — mỗi chân như thế phải có một Fact khác đứng sau.

## Fact trong kho (14)

| Chủ đề | Khoá | Giá trị | Tầng | Trích dẫn |
|---|---|---|---|---|
| `chip:STM32F469NI` | flash.size | 7.0 | BAC | CMSIS-STM32F469XX-H · dòng 1241–1280 |
| `config:flash` | config:flash.size | 2097152.0 | CAUHINH | ? · **KHÔNG CÓ** |
| `config:flash` | config:flash.origin | None | CAUHINH | ? · **KHÔNG CÓ** |
| `config:ram` | config:ram.size | 327680.0 | CAUHINH | ? · **KHÔNG CÓ** |
| `config:ram` | config:ram.origin | None | CAUHINH | ? · **KHÔNG CÓ** |
| `chip:STM32F469NI` | led1.pin | PG6 | BAC | BSP-STM32469I-DISCO-H · dòng 121–160 |
| `chip:STM32F469NI` | led2.pin | PD4 | BAC | BSP-STM32469I-DISCO-H · dòng 121–160 |
| `chip:STM32F469NI` | led3.pin | PD5 | BAC | BSP-STM32469I-DISCO-H · dòng 121–160 |
| `chip:STM32F469NI` | led4.pin | PK3 | BAC | BSP-STM32469I-DISCO-H · dòng 121–160 |
| `chip:STM32F469NI` | button.port | GPIOA | BAC | BSP-STM32469I-DISCO-H · dòng 161–200 |
| `chip:STM32F469NI` | button.pin | GPIO_PIN_0 | BAC | BSP-STM32469I-DISCO-H · dòng 161–200 |
| `chip:STM32F469NI` | button.exti_mode | GPIO_MODE_IT_RISING | BAC | BSP-STM32469I-DISCO-C · dòng 281–320 |
| `chip:STM32F469NI` | led.on_state | GPIO_PIN_RESET | BAC | BSP-STM32469I-DISCO-C · dòng 241–280 |
| `chip:STM32F469NI` | led.off_state | GPIO_PIN_SET | BAC | BSP-STM32469I-DISCO-C · dòng 161–200 |

## Biên dịch

- **dat**: `True`
- **cong_cu**: `arm-none-eabi-gcc`
- **so_loi**: `0`
- **so_canh_bao**: `0`
- **tep_ra**: `.eide/build/mach.hex`
- **tep_bin**: `.eide/build/mach.bin`
- **thieu_libc**: `True`
- **flash**: `492`
- **sram**: `0`
- **flash_toi_da**: `20971520`
- **sram_toi_da**: `3276800`
- **ty_le_flash**: `0.0`
- **ty_le_sram**: `0.0`
- **vi_sao_khong_dat**: ``

## Nạp vào bo

- **dat**: `True`
- **cach**: `st-flash`
- **tep**: `mach.bin`
- **so_byte**: `492`
- **hash**: `f351053423cc90824d7aca3c3d8290f611e35ba07bd54de2ea4c02e109b1bfde`
- **dich**: `0x08000000`
- **giay**: `0.4`
- **da_verify**: `True`
- **chip_da_doi_chieu**: `STM32F46x_F47x`
- **vi_sao_khong_dat**: ``
- **chip_du_an**: `STM32F469NI`
- **chip_theo_nhan_o**: `STM32F469NI`
- **reversible**: `False`
- **vi_sao_khong_hoan_tac**: `Ghi đè Flash của chip; bản cũ không còn.`

## Log từ bo

- **cong**: `/dev/cu.usbmodem103`
- **baud**: `115200`
- **giay**: `3`
- **so_byte**: `0`
- **im_lang**: `True`
