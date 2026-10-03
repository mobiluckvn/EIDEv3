// tb_soc_run.v
// Top-level testbench mô phỏng toàn hệ thống SoC Bài 1 cho hdl.sim
`timescale 1ns / 1ps

`include "tai-lieu/picorv32.v"
`include "bai1/rtl/reset_gen.v"
`include "bai1/rtl/bram_mem.v"
`include "bai1/rtl/uart_tx.v"
`include "bai1/rtl/gpio_led.v"
`include "bai1/rtl/bus_interconnect.v"
`include "bai1/rtl/soc_top.v"
`include "bai1/sim/uart_rx_model.v"

module tb_soc_run;

    reg clk;
    reg btn_s1;
    wire uart_tx_line;
    wire [5:0] leds;

    // Chu kỳ 27 MHz: 37.037 ns (nửa chu kỳ 18.518 ns)
    initial begin
        clk = 1'b0;
        forever #18.518 clk = ~clk;
    end

    initial begin
        btn_s1 = 1'b1;
    end

    // Khởi tạo SoC với firmware.hex
    soc_top #(
        .CLK_FREQ (27_000_000),
        .BAUD     (115_200),
        .HEX_FILE ("firmware.hex")
    ) u_dut (
        .clk     (clk),
        .btn_s1  (btn_s1),
        .uart_tx (uart_tx_line),
        .led     (leds)
    );

    // Bộ thu UART mô hình
    wire       rx_valid;
    wire [7:0] rx_byte;

    uart_rx_model #(
        .CLK_FREQ (27_000_000),
        .BAUD     (115_200)
    ) u_rx (
        .clk       (clk),
        .rst_n     (1'b1),
        .rx_serial (uart_tx_line),
        .rx_valid  (rx_valid),
        .rx_byte   (rx_byte)
    );

    // Debug probe
    integer dbg_trans = 0;
    initial begin
        #100;
        $display("[TB CHECK] mem[0]=%h mem[24]=%h", u_dut.u_bram.mem[0], u_dut.u_bram.mem[24]);
    end
    always @(posedge clk) begin
        if (u_dut.cpu_trap) begin
            $display("[TB ERROR] CPU TRAP tai thoi diem %0t ns! PC/Addr = %h", $time, u_dut.cpu_mem_addr);
            $finish;
        end
        if (u_dut.uart_tx_start) begin
            $display("[TB UART] Ghi byte: %c (0x%02h) tai %0t ns", u_dut.uart_tx_data, u_dut.uart_tx_data, $time);
        end
        if (u_dut.cpu_mem_valid && u_dut.cpu_mem_ready && dbg_trans < 50) begin
            dbg_trans <= dbg_trans + 1;
            $display("[TB CPU #%0d] Instr=%b Addr=%h Wdata=%h Rdata=%h",
                     dbg_trans, u_dut.cpu_mem_instr, u_dut.cpu_mem_addr, u_dut.cpu_mem_wdata, u_dut.cpu_mem_rdata);
        end
    end

    // Bắt và đối soát chuỗi (36 ký tự)
    reg [8*36-1:0] shift_window = 0;
    integer match_count = 0;

    // Giám sát và kiểm tra LED đổi trạng thái (nháy)
    reg [5:0] last_leds = 6'bxxxxxx;
    integer led_toggle_count = 0;

    always @(posedge clk) begin
        if (last_leds === 6'bxxxxxx) begin
            last_leds <= leds;
        end else if (leds !== last_leds) begin
            led_toggle_count <= led_toggle_count + 1;
            $display("[TB LED] LED doi trang thai: %b -> %b tai %0t ns (lan %0d)", last_leds, leds, $time, led_toggle_count + 1);
            last_leds <= leds;
        end
    end

    always @(posedge clk) begin
        if (rx_valid) begin
            shift_window <= {shift_window[8*35-1:0], rx_byte};
            if ({shift_window[8*35-1:0], rx_byte} == "Hello from PicoRV32 on Tang Nano 20K") begin
                match_count <= match_count + 1;
                $display("\n[TB] Phat hien chuoi lan thu %0d tai thoi diem %0t ns", match_count + 1, $time);
                if (match_count + 1 >= 2) begin
                    if (led_toggle_count < 1) begin
                        $display("\n==========================================");
                        $display("  KET QUA MO PHONG: FAIL");
                        $display("  Loi: LED khong doi trang thai (toggle count = %0d)!", led_toggle_count);
                        $display("==========================================\n");
                        $finish;
                    end else begin
                        $display("\n==========================================");
                        $display("  KET QUA MO PHONG: PASS");
                        $display("  Da nhan dung chuoi it nhat 2 lan va LED da nhay (%0d lan)!", led_toggle_count);
                        $display("==========================================\n");
                        $finish;
                    end
                end
            end
        end
    end

    // Giới hạn thời gian timeout 20 ms
    initial begin
        #20000000;
        $display("\n==========================================");
        $display("  KET QUA MO PHONG: FAIL");
        $display("  Het thoi gian cho (Timeout)! So lan nhan: %0d, So lan LED doi: %0d", match_count, led_toggle_count);
        $display("==========================================\n");
        $finish;
    end

endmodule
