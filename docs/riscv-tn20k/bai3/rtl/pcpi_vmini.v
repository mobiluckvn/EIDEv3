`timescale 1ns / 1ps

// =============================================================================
// Mô-đun: pcpi_vmini
// Chức năng: Đơn vị Vector Mini (Nấc 3c - Tiền RVV) cho CPU PicoRV32
//
// Tập lệnh tuỳ biến custom-0 (opcode = 7'b0001011, funct7 = 7'b0000000):
//   - funct3 = 000: acc.clr          (acc <= 0)                      [1 ck]
//   - funct3 = 001: mac rs1, rs2     (acc <= acc + rs1 * rs2)         [1 ck]
//   - funct3 = 010: acc.rd rd        (rd <= acc)                      [1 ck]
//   - funct3 = 011: dot4 rs1, rs2    (acc <= acc + sum(4x int8*int8)) [1 ck]
//   - funct3 = 100: vsetvl rd, rs1   (VL <= min(rs1, 16), rd <= VL)   [1 ck]
//   - funct3 = 101: vload vd, rs1    (nạp VL byte từ BRAM Port B)     [6 ck]
//   - funct3 = 110: vdot vs1, vs2    (tích luỹ tích vô hướng vector)  [4 ck]
//   - funct3 = 111: vstore vs, rs1   (ghi VL byte ra BRAM Port B)     [6 ck]
// =============================================================================

module pcpi_vmini (
    input  wire        clk,
    input  wire        resetn,

    // Giao diện Pico Co-Processor Interface (PCPI)
    input  wire        pcpi_valid,
    input  wire [31:0] pcpi_insn,
    input  wire [31:0] pcpi_rs1,
    input  wire [31:0] pcpi_rs2,
    output wire        pcpi_wr,
    output wire [31:0] pcpi_rd,
    output wire        pcpi_wait,
    output wire        pcpi_ready,

    // Giao diện BRAM Port B (True Dual-Port)
    output reg         vmem_en,
    output reg  [31:0] vmem_addr,
    output reg  [31:0] vmem_wdata,
    output reg  [3:0]  vmem_wstrb,
    input  wire [31:0] vmem_rdata
);

    // -------------------------------------------------------------------------
    // 1. Giải mã lệnh chặt chẽ (Decoder Lock chống Funct7/Funct3 Aliasing)
    // -------------------------------------------------------------------------
    wire [6:0] opcode = pcpi_insn[6:0];
    wire [2:0] funct3 = pcpi_insn[14:12];
    wire [6:0] funct7 = pcpi_insn[31:25];

    // Chỉ nhận diện khi opcode == custom-0 và funct7 == 0000000 đúng chuẩn
    wire is_custom0 = pcpi_valid && (opcode == 7'b0001011) && (funct7 == 7'b0000000);

    // Lệnh 1 chu kỳ
    wire is_acc_clr = is_custom0 && (funct3 == 3'b000);
    wire is_mac     = is_custom0 && (funct3 == 3'b001);
    wire is_acc_rd  = is_custom0 && (funct3 == 3'b010);
    wire is_dot4    = is_custom0 && (funct3 == 3'b011);
    wire is_vsetvl  = is_custom0 && (funct3 == 3'b100);

    // Lệnh nhiều chu kỳ (có kiểm tra căn chỉnh địa chỉ 4-byte cho BRAM)
    wire addr_aligned = (pcpi_rs1[1:0] == 2'b00);
    wire is_vload_req = is_custom0 && (funct3 == 3'b101);
    wire is_vdot_req  = is_custom0 && (funct3 == 3'b110);
    wire is_vstore_req= is_custom0 && (funct3 == 3'b111);

    // Chỉ thực thi load/store nếu địa chỉ căn chỉnh 4-byte
    wire is_vload  = is_vload_req && addr_aligned;
    wire is_vstore = is_vstore_req && addr_aligned;
    wire is_vdot   = is_vdot_req;

    // Chỉ số thanh ghi
    wire [1:0] reg_vd  = pcpi_insn[8:7];   // 4 thanh ghi vector v0..v3
    wire [1:0] reg_vs1 = pcpi_insn[16:15];
    wire [1:0] reg_vs2 = pcpi_insn[21:20];

    // -------------------------------------------------------------------------
    // 2. Tệp thanh ghi vector (4 x 128-bit) và chiều dài vector VL
    // -------------------------------------------------------------------------
    reg [127:0] vreg [0:3];
    reg [4:0]   vl; // Chiều dài vector (0 đến 16), mặc định 16

    wire [4:0] next_vl = (pcpi_rs1 > 32'd16) ? 5'd16 : pcpi_rs1[4:0];

    // -------------------------------------------------------------------------
    // 3. FSM điều khiển các lệnh nhiều chu kỳ (vload, vdot, vstore)
    // -------------------------------------------------------------------------
    localparam STATE_IDLE   = 2'd0;
    localparam STATE_LOAD   = 2'd1;
    localparam STATE_DOT    = 2'd2;
    localparam STATE_STORE  = 2'd3;

    reg [1:0] state;
    reg [2:0] step;
    reg       reg_wait;
    reg       reg_ready;
    reg [1:0] active_vd;
    reg [1:0] active_vs1;
    reg [1:0] active_vs2;
    reg [31:0] base_addr;

    // Thanh ghi tích luỹ acc (32-bit có dấu)
    reg signed [31:0] acc;

    // -------------------------------------------------------------------------
    // 4. Bốn bộ nhân 8x8 có dấu dùng chung cho dot4 và vdot
    // -------------------------------------------------------------------------
    reg signed [7:0] m_a0, m_a1, m_a2, m_a3;
    reg signed [7:0] m_b0, m_b1, m_b2, m_b3;

    wire signed [15:0] p0 = m_a0 * m_b0;
    wire signed [15:0] p1 = m_a1 * m_b1;
    wire signed [15:0] p2 = m_a2 * m_b2;
    wire signed [15:0] p3 = m_a3 * m_b3;

    wire signed [31:0] sum4 = {{16{p0[15]}}, p0} +
                              {{16{p1[15]}}, p1} +
                              {{16{p2[15]}}, p2} +
                              {{16{p3[15]}}, p3};

    // Chọn dữ liệu ngõ vào cho 4 bộ nhân tuỳ theo lệnh và chu kỳ
    // Mask về 0 nếu chỉ số byte >= VL (đáp ứng Phép phá mã 6)
    always @(*) begin
        if (state == STATE_DOT) begin
            case (step)
                3'd0: begin
                    m_a0 = (vl > 5'd0)  ? $signed(vreg[active_vs1][  7:  0]) : 8'sd0;
                    m_b0 = (vl > 5'd0)  ? $signed(vreg[active_vs2][  7:  0]) : 8'sd0;
                    m_a1 = (vl > 5'd1)  ? $signed(vreg[active_vs1][ 15:  8]) : 8'sd0;
                    m_b1 = (vl > 5'd1)  ? $signed(vreg[active_vs2][ 15:  8]) : 8'sd0;
                    m_a2 = (vl > 5'd2)  ? $signed(vreg[active_vs1][ 23: 16]) : 8'sd0;
                    m_b2 = (vl > 5'd2)  ? $signed(vreg[active_vs2][ 23: 16]) : 8'sd0;
                    m_a3 = (vl > 5'd3)  ? $signed(vreg[active_vs1][ 31: 24]) : 8'sd0;
                    m_b3 = (vl > 5'd3)  ? $signed(vreg[active_vs2][ 31: 24]) : 8'sd0;
                end
                3'd1: begin
                    m_a0 = (vl > 5'd4)  ? $signed(vreg[active_vs1][ 39: 32]) : 8'sd0;
                    m_b0 = (vl > 5'd4)  ? $signed(vreg[active_vs2][ 39: 32]) : 8'sd0;
                    m_a1 = (vl > 5'd5)  ? $signed(vreg[active_vs1][ 47: 40]) : 8'sd0;
                    m_b1 = (vl > 5'd5)  ? $signed(vreg[active_vs2][ 47: 40]) : 8'sd0;
                    m_a2 = (vl > 5'd6)  ? $signed(vreg[active_vs1][ 55: 48]) : 8'sd0;
                    m_b2 = (vl > 5'd6)  ? $signed(vreg[active_vs2][ 55: 48]) : 8'sd0;
                    m_a3 = (vl > 5'd7)  ? $signed(vreg[active_vs1][ 63: 56]) : 8'sd0;
                    m_b3 = (vl > 5'd7)  ? $signed(vreg[active_vs2][ 63: 56]) : 8'sd0;
                end
                3'd2: begin
                    m_a0 = (vl > 5'd8)  ? $signed(vreg[active_vs1][ 71: 64]) : 8'sd0;
                    m_b0 = (vl > 5'd8)  ? $signed(vreg[active_vs2][ 71: 64]) : 8'sd0;
                    m_a1 = (vl > 5'd9)  ? $signed(vreg[active_vs1][ 79: 72]) : 8'sd0;
                    m_b1 = (vl > 5'd9)  ? $signed(vreg[active_vs2][ 79: 72]) : 8'sd0;
                    m_a2 = (vl > 5'd10) ? $signed(vreg[active_vs1][ 87: 80]) : 8'sd0;
                    m_b2 = (vl > 5'd10) ? $signed(vreg[active_vs2][ 87: 80]) : 8'sd0;
                    m_a3 = (vl > 5'd11) ? $signed(vreg[active_vs1][ 95: 88]) : 8'sd0;
                    m_b3 = (vl > 5'd11) ? $signed(vreg[active_vs2][ 95: 88]) : 8'sd0;
                end
                default: begin // step == 3'd3
                    m_a0 = (vl > 5'd12) ? $signed(vreg[active_vs1][103: 96]) : 8'sd0;
                    m_b0 = (vl > 5'd12) ? $signed(vreg[active_vs2][103: 96]) : 8'sd0;
                    m_a1 = (vl > 5'd13) ? $signed(vreg[active_vs1][111:104]) : 8'sd0;
                    m_b1 = (vl > 5'd13) ? $signed(vreg[active_vs2][111:104]) : 8'sd0;
                    m_a2 = (vl > 5'd14) ? $signed(vreg[active_vs1][119:112]) : 8'sd0;
                    m_b2 = (vl > 5'd14) ? $signed(vreg[active_vs2][119:112]) : 8'sd0;
                    m_a3 = (vl > 5'd15) ? $signed(vreg[active_vs1][127:120]) : 8'sd0;
                    m_b3 = (vl > 5'd15) ? $signed(vreg[active_vs2][127:120]) : 8'sd0;
                end
            endcase
        end else begin
            // Cho lệnh dot4 vô hướng 1 chu kỳ
            m_a0 = $signed(pcpi_rs1[ 7: 0]);
            m_b0 = $signed(pcpi_rs2[ 7: 0]);
            m_a1 = $signed(pcpi_rs1[15: 8]);
            m_b1 = $signed(pcpi_rs2[15: 8]);
            m_a2 = $signed(pcpi_rs1[23:16]);
            m_b2 = $signed(pcpi_rs2[23:16]);
            m_a3 = $signed(pcpi_rs1[31:24]);
            m_b3 = $signed(pcpi_rs2[31:24]);
        end
    end

    // -------------------------------------------------------------------------
    // 5. Tiến trình FSM và Cập nhật Trạng thái
    // -------------------------------------------------------------------------
    always @(posedge clk) begin
        if (!resetn) begin
            state       <= STATE_IDLE;
            step        <= 3'd0;
            reg_wait    <= 1'b0;
            reg_ready   <= 1'b0;
            vl          <= 5'd16;
            acc         <= 32'sd0;
            vmem_en     <= 1'b0;
            vmem_addr   <= 32'd0;
            vmem_wdata  <= 32'd0;
            vmem_wstrb  <= 4'b0000;
            active_vd   <= 2'd0;
            active_vs1  <= 2'd0;
            active_vs2  <= 2'd0;
            base_addr   <= 32'd0;
            vreg[0]     <= 128'd0;
            vreg[1]     <= 128'd0;
            vreg[2]     <= 128'd0;
            vreg[3]     <= 128'd0;
        end else begin
            case (state)
                STATE_IDLE: begin
                    reg_ready  <= 1'b0;
                    vmem_en    <= 1'b0;
                    vmem_wstrb <= 4'b0000;

                    if (pcpi_valid) begin
                        // Lệnh 1 chu kỳ
                        if (is_acc_clr) begin
                            acc <= 32'sd0;
                        end else if (is_mac) begin
                            acc <= acc + ($signed(pcpi_rs1) * $signed(pcpi_rs2));
                        end else if (is_dot4) begin
                            acc <= acc + sum4;
                        end else if (is_vsetvl) begin
                            vl <= next_vl;
                        end
                        // Lệnh vload nhiều chu kỳ qua BRAM Port B (6 chu kỳ)
                        else if (is_vload) begin
                            active_vd  <= reg_vd;
                            base_addr  <= pcpi_rs1;
                            state      <= STATE_LOAD;
                            step       <= 3'd0;
                            reg_wait   <= 1'b1;
                            // Bắt đầu đọc từ 0 ngay chu kỳ 0
                            vmem_en    <= 1'b1;
                            vmem_addr  <= pcpi_rs1;
                            vmem_wstrb <= 4'b0000;
                        end
                        // Lệnh vdot nhiều chu kỳ (4 chu kỳ)
                        else if (is_vdot) begin
                            active_vs1 <= reg_vs1;
                            active_vs2 <= reg_vs2;
                            state      <= STATE_DOT;
                            step       <= 3'd0;
                            reg_wait   <= 1'b1;
                        end
                        // Lệnh vstore nhiều chu kỳ qua BRAM Port B (6 chu kỳ)
                        else if (is_vstore) begin
                            active_vs2 <= reg_vs2;
                            base_addr  <= pcpi_rs1;
                            state      <= STATE_STORE;
                            step       <= 3'd0;
                            reg_wait   <= 1'b1;
                            // Ghi từ 0
                            vmem_en    <= 1'b1;
                            vmem_addr  <= pcpi_rs1;
                            vmem_wdata <= vreg[reg_vs2][31:0];
                            vmem_wstrb <= 4'b1111;
                        end
                    end
                end

                // FSM nạp 4 từ gối đầu (pipelined BRAM read): đúng 6 chu kỳ
                STATE_LOAD: begin
                    case (step)
                        3'd0: begin // Chu kỳ 1: phát addr 1
                            vmem_addr <= base_addr + 32'd4;
                            step      <= 3'd1;
                        end
                        3'd1: begin // Chu kỳ 2: nhận data 0, phát addr 2
                            vreg[active_vd][31:0] <= vmem_rdata;
                            vmem_addr <= base_addr + 32'd8;
                            step      <= 3'd2;
                        end
                        3'd2: begin // Chu kỳ 3: nhận data 1, phát addr 3
                            vreg[active_vd][63:32] <= vmem_rdata;
                            vmem_addr <= base_addr + 32'd12;
                            step      <= 3'd3;
                        end
                        3'd3: begin // Chu kỳ 4: nhận data 2, ngừng phát addr
                            vreg[active_vd][95:64] <= vmem_rdata;
                            vmem_en   <= 1'b0;
                            step      <= 3'd4;
                        end
                        3'd4: begin // Chu kỳ 5: nhận data 3, hạ wait, báo ready
                            vreg[active_vd][127:96] <= vmem_rdata;
                            reg_wait  <= 1'b0;
                            reg_ready <= 1'b1;
                            step      <= 3'd5;
                        end
                        default: begin // Chu kỳ 6: hoàn tất, trở về IDLE
                            reg_ready <= 1'b0;
                            state     <= STATE_IDLE;
                        end
                    endcase
                end

                // FSM tính tích vô hướng 4 làn song song: 4 chu kỳ
                STATE_DOT: begin
                    acc <= acc + sum4;
                    case (step)
                        3'd0: step <= 3'd1;
                        3'd1: step <= 3'd2;
                        3'd2: begin
                            step      <= 3'd3;
                            reg_wait  <= 1'b0;
                            reg_ready <= 1'b1;
                        end
                        default: begin
                            reg_ready <= 1'b0;
                            state     <= STATE_IDLE;
                        end
                    endcase
                end

                // FSM ghi 4 từ ra BRAM Port B (dự phòng): 6 chu kỳ
                STATE_STORE: begin
                    case (step)
                        3'd0: begin
                            vmem_addr  <= base_addr + 32'd4;
                            vmem_wdata <= vreg[active_vs2][63:32];
                            step       <= 3'd1;
                        end
                        3'd1: begin
                            vmem_addr  <= base_addr + 32'd8;
                            vmem_wdata <= vreg[active_vs2][95:64];
                            step       <= 3'd2;
                        end
                        3'd2: begin
                            vmem_addr  <= base_addr + 32'd12;
                            vmem_wdata <= vreg[active_vs2][127:96];
                            step       <= 3'd3;
                        end
                        3'd3: begin
                            vmem_en    <= 1'b0;
                            vmem_wstrb <= 4'b0000;
                            reg_wait   <= 1'b0;
                            reg_ready  <= 1'b1;
                            step       <= 3'd4;
                        end
                        default: begin
                            reg_ready <= 1'b0;
                            state     <= STATE_IDLE;
                        end
                    endcase
                end
            endcase
        end
    end

    // -------------------------------------------------------------------------
    // 6. Giao diện PCPI handshake
    // -------------------------------------------------------------------------
    // Kéo pcpi_wait ngay lập tức ở chu kỳ 0 bằng mạch tổ hợp nếu lệnh bắt đầu
    wire start_wait = (state == STATE_IDLE) && pcpi_valid && (is_vload || is_vdot || is_vstore);
    assign pcpi_wait = start_wait || reg_wait;

    // Lệnh 1 chu kỳ trả ready ngay khi pcpi_valid; lệnh nhiều chu kỳ dùng reg_ready
    wire is_1cycle = is_acc_clr || is_mac || is_acc_rd || is_dot4 || is_vsetvl;
    assign pcpi_ready = is_1cycle ? 1'b1 : reg_ready;

    // Trả kết quả ghi vào thanh ghi CPU cho acc.rd và vsetvl
    assign pcpi_wr = is_acc_rd || is_vsetvl;
    assign pcpi_rd = is_acc_rd  ? acc :
                     is_vsetvl  ? {27'd0, next_vl} :
                     32'd0;

endmodule
