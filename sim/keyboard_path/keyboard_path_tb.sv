// Focused keyboard-path check for the XT peripheral contract.
// It models one Set-2 Enter frame and the BIOS PPI clear pulse.
`timescale 1ns/1ps

module keyboard_path_tb;
    logic clock = 1'b0;
    always #5 clock = ~clock;

    logic reset = 1'b1;
    logic peripheral_ce = 1'b1;
    logic device_clock = 1'b1;
    logic device_data = 1'b1;
    logic clear_keycode;
    logic key_irq;
    logic [7:0] keycode;
    logic pause_core;

    KFPS2KB u_keyboard (
        .clock(clock), .peripheral_ce(peripheral_ce), .reset(reset),
        .device_clock(device_clock), .device_data(device_data),
        .irq(key_irq), .keycode(keycode), .clear_keycode(clear_keycode),
        .pause_core(pause_core)
    );

    logic ppi_cs_n = 1'b1;
    logic ppi_rd_n = 1'b1;
    logic ppi_wr_n = 1'b1;
    logic [1:0] ppi_addr = 2'b00;
    logic [7:0] ppi_bus_in = 8'h00;
    wire [7:0] ppi_bus_out;
    wire [7:0] ppi_port_a_in = keycode;
    wire [7:0] ppi_port_a_out;
    wire ppi_port_a_io;
    wire [7:0] ppi_port_b_in = 8'h00;
    wire [7:0] ppi_port_b_out;
    wire ppi_port_b_io;
    wire [7:0] ppi_port_c_in = 8'h00;
    wire [7:0] ppi_port_c_out;
    wire [7:0] ppi_port_c_io;

    assign clear_keycode = ppi_port_b_out[7];

    KF8255 u_ppi (
        .clock(clock), .reset(reset), .chip_select_n(ppi_cs_n),
        .read_enable_n(ppi_rd_n), .write_enable_n(ppi_wr_n),
        .address(ppi_addr), .data_bus_in(ppi_bus_in),
        .data_bus_out(ppi_bus_out),
        .port_a_in(ppi_port_a_in), .port_a_out(ppi_port_a_out),
        .port_a_io(ppi_port_a_io), .port_b_in(ppi_port_b_in),
        .port_b_out(ppi_port_b_out), .port_b_io(ppi_port_b_io),
        .port_c_in(ppi_port_c_in), .port_c_out(ppi_port_c_out),
        .port_c_io(ppi_port_c_io)
    );

    logic pic_cs_n = 1'b1;
    logic pic_rd_n = 1'b1;
    logic pic_wr_n = 1'b1;
    logic pic_addr = 1'b0;
    logic [7:0] pic_bus_in = 8'h00;
    wire [7:0] pic_bus_out;
    wire pic_bus_io;
    wire pic_buffer_enable;
    wire pic_sp_en;
    wire [2:0] cascade_out;
    wire cascade_io;
    logic inta_n = 1'b1;
    wire pic_int;
    wire [7:0] pic_ir = {6'b0, key_irq, 1'b0};

    KF8259 u_pic (
        .clock(clock), .reset(reset), .chip_select_n(pic_cs_n),
        .read_enable_n(pic_rd_n), .write_enable_n(pic_wr_n),
        .address(pic_addr), .data_bus_in(pic_bus_in),
        .data_bus_out(pic_bus_out), .data_bus_io(pic_bus_io),
        .cascade_in(3'b000), .cascade_out(cascade_out),
        .cascade_io(cascade_io), .slave_program_n(1'b1),
        .buffer_enable(pic_buffer_enable),
        .slave_program_or_enable_buffer(pic_sp_en),
        .interrupt_acknowledge_n(inta_n), .interrupt_to_cpu(pic_int),
        .interrupt_request(pic_ir)
    );

    task automatic ppi_write(input logic [1:0] address, input logic [7:0] data);
        begin
            @(negedge clock);
            ppi_addr <= address; ppi_bus_in <= data;
            ppi_cs_n <= 1'b0; ppi_wr_n <= 1'b0;
            repeat (2) @(negedge clock);
            ppi_wr_n <= 1'b1;
            repeat (2) @(negedge clock);
            ppi_cs_n <= 1'b1;
        end
    endtask

    task automatic pic_write(input logic address, input logic [7:0] data);
        begin
            @(negedge clock);
            pic_addr <= address; pic_bus_in <= data;
            pic_cs_n <= 1'b0; pic_wr_n <= 1'b0;
            repeat (2) @(negedge clock);
            pic_wr_n <= 1'b1;
            repeat (2) @(negedge clock);
            pic_cs_n <= 1'b1;
        end
    endtask

    task automatic send_set2(input logic [7:0] code);
        logic [10:0] frame;
        logic [7:0] code_lsb_first;
        integer i;
        begin
            // The shift register samples start, eight LSB-first data bits,
            // parity and stop on successive falling clock edges.
            code_lsb_first = {code[0], code[1], code[2], code[3],
                              code[4], code[5], code[6], code[7]};
            frame = {1'b0, code_lsb_first, ~(^code), 1'b1};
            device_clock <= 1'b1;
            device_data <= frame[10];
            repeat (2) @(negedge clock);
            device_clock <= 1'b0;
            repeat (2) @(negedge clock);
            for (i = 9; i >= 0; i = i - 1) begin
                device_clock <= 1'b1;
                device_data <= frame[i];
                repeat (2) @(negedge clock);
                device_clock <= 1'b0;
                repeat (2) @(negedge clock);
            end
            device_clock <= 1'b1;
            device_data <= 1'b1;
            repeat (4) @(negedge clock);
        end
    endtask

    initial begin
        repeat (4) @(negedge clock);
        reset <= 1'b0;
        repeat (4) @(negedge clock);

        // BIOS-equivalent PPI and PIC setup.
        ppi_write(2'b11, 8'h99);
        ppi_write(2'b01, 8'h40);
        pic_write(1'b0, 8'h13);
        pic_write(1'b1, 8'h08);
        pic_write(1'b1, 8'h09);
        pic_write(1'b1, 8'hBC);

        send_set2(8'h5A); // Enter -> XT 1Ch
        repeat (4) @(negedge clock);
        if (key_irq !== 1'b1 || keycode !== 8'h1C)
            $fatal(1, "keyboard decode failed: irq=%b keycode=%02h", key_irq, keycode);
        if (pic_int !== 1'b1)
            $fatal(1, "IRQ1 did not reach the PIC INT output");

        // BIOS int 09 acknowledges the byte by pulsing PPI port-B bit 7.
        ppi_write(2'b01, 8'hC0);
        ppi_write(2'b01, 8'h40);
        repeat (2) @(negedge clock);
        if (key_irq !== 1'b0)
            $fatal(1, "keyboard IRQ did not clear after the BIOS pulse");

        $display("keyboard_path_tb PASS: Enter -> XT 1C, IRQ1 asserted and cleared");
        $finish;
    end
endmodule
