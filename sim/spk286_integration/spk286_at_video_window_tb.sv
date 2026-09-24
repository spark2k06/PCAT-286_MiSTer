`timescale 1ns/1ps

// Program the production AT video adapter through its CPU request mailbox.
// Every dot emitted in the rendered EGA window must survive the blanking
// sent to the HDMI mixer/capture, including the last text column.
module spk286_at_video_window_tb;
    logic clk = 0, clk_video = 0, reset = 1;
    always #10 clk = ~clk;
    always #17.462 clk_video = ~clk_video;
    logic valid = 0, command_valid = 0, write_cycle = 0, io_cycle = 1;
    logic [23:0] address = 0;
    logic [1:0] lanes = 1;
    logic [15:0] data_out = 0;
    wire accept, ready;
    wire [15:0] data_in;
    wire hblank, vblank, de, dot;
    logic [3:0] h_offset = 0;

    spk286_at_video_adapter dut (
        .clk(clk), .reset(reset), .clk_video(clk_video), .splashscreen(1'b0),
        .ega_monitor_profile(2'd0), .vga_enabled(1'b0), .vga_mode13_native(1'b1),
        .crt_h_offset(h_offset), .crt_v_offset(3'd0),
        .vsync_width_osd(3'd0), .hsync_width_osd(3'd0),
        .request_valid(valid), .request_command_valid(command_valid),
        .request_write(write_cycle), .request_io(io_cycle),
        .request_address(address), .request_byte_enable(lanes),
        .request_data_out(data_out), .request_accept(accept), .request_ready(ready),
        .request_read_data(data_in), .request_read_data_valid(),
        .video_hblank(hblank), .video_vblank(vblank), .video_de(de),
        .video_dot_toggle(dot)
    );

    task automatic access_byte(input logic wr, io,
                               input logic [23:0] addr, input logic [7:0] value);
        integer cycles;
        begin
            @(negedge clk);
            valid = 1;
            command_valid = 1;
            write_cycle = wr;
            io_cycle = io;
            address = addr;
            lanes = addr[0] ? 2'b10 : 2'b01;
            data_out = addr[0] ? {value, 8'h00} : {8'h00, value};
            #1;
            if (!accept) $fatal(1, "Video request rejected at %06h", addr);
            @(negedge clk);
            command_valid = 0;
            cycles = 0;
            while (!ready && cycles < 256) begin
                @(negedge clk);
                cycles++;
            end
            if (!ready) $fatal(1, "Video request timed out at %06h", addr);
            @(negedge clk);
            valid = 0;
            repeat (2) @(negedge clk);
        end
    endtask

    task automatic io_write(input logic [15:0] port, input logic [7:0] value);
        access_byte(1, 1, {8'd0, port}, value);
    endtask

    task automatic indexed_write(input logic [15:0] port, input logic [7:0] index, value);
        begin
            io_write(port, index);
            io_write(port + 1, value);
        end
    endtask

    task automatic attr_write(input logic [7:0] index, value);
        begin
            access_byte(0, 1, 24'h0003DA, 0);
            io_write(16'h03C0, index);
            io_write(16'h03C0, value);
            io_write(16'h03C0, 8'h20);
        end
    endtask

    logic [7:0] crtc [0:24];
    integer mode, offset_index;
    task automatic program_mode(input integer mode_number);
        begin
            // Standard BIOS 80-column text, 200 or 350 scanlines. Mode 2
            // reuses the 200-line CRTC for 640x200 planar graphics.
            if (mode_number == 1) begin
                crtc = '{8'h5B,8'h4F,8'h53,8'h37,8'h52,8'h00,8'h6C,8'h1F,
                         8'h00,8'h0D,8'h0B,8'h0C,8'h00,8'h00,8'h00,8'h00,
                         8'h5E,8'h2B,8'h5D,8'h28,8'h0F,8'h5E,8'h0A,8'hA3,8'hFF};
            end else begin
                crtc = '{8'h70,8'h4F,8'h5C,8'h2F,8'h5F,8'h07,8'h04,8'h11,
                         8'h00,8'h07,8'h06,8'h07,8'h00,8'h00,8'h00,8'h00,
                         8'hE1,8'h24,8'hC7,8'h28,8'h08,8'hE0,8'hF0,8'hA3,8'hFF};
                if (mode_number == 2) begin
                    crtc[2]=8'h59; crtc[3]=8'h2D; crtc[4]=8'h5E; crtc[5]=8'h06;
                    crtc[9]=8'h01; crtc[16]=8'hE0; crtc[17]=8'h23;
                    crtc[20]=8'h00; crtc[21]=8'hDF; crtc[22]=8'hEF; crtc[23]=8'hC2;
                end
            end
            io_write(16'h03C2, mode_number == 1 ? 8'hA7 : 8'h23);
            indexed_write(16'h03C4, 1, 8'h01);
            indexed_write(16'h03C4, 2, mode_number == 2 ? 8'h0F : 8'h03);
            indexed_write(16'h03C4, 3, 0);
            indexed_write(16'h03C4, 4, mode_number == 2 ? 8'h06 : 8'h03);
            for (integer j = 0; j <= 24; j++) indexed_write(16'h03D4, 8'(j), crtc[j]);
            for (integer j = 0; j < 16; j++) attr_write(8'(j), 8'(j));
            attr_write(8'h10, mode_number == 2 ? 8'h01 : 8'h08);
            attr_write(8'h11, 0);
            attr_write(8'h12, 8'h0F);
            attr_write(8'h13, 0);
            indexed_write(16'h03CE, 5, mode_number == 2 ? 8'h00 : 8'h10);
            indexed_write(16'h03CE, 6, mode_number == 2 ? 8'h0D : 8'h0E);
            indexed_write(16'h03CE, 8, 8'hFF);
            // A real VRAM write arms the display activation state machine.
            access_byte(1, 0, 24'h0B8000, 8'h41);
        end
    endtask

    task automatic next_dot;
        logic previous_dot;
        begin
            previous_dot = dot;
            do @(negedge clk_video); while (dot == previous_dot);
        end
    endtask

    integer width, clipped;
    task automatic measure_line;
        begin
            // Start in blanking, then observe an entire rendered scanline.
            while (de) next_dot();
            while (!de) next_dot();
            width = 0;
            clipped = 0;
            while (de) begin
                width++;
                if (hblank || vblank) clipped++;
                next_dot();
            end
            $display("AT_VIDEO_WINDOW mode=%0d offset=%0d rendered=%0d clipped=%0d",
                     mode, h_offset, width, clipped);
            if (width != 640 || clipped != 0)
                $fatal(1, "HDMI blanking loses rendered pixels: width=%0d clipped=%0d", width, clipped);
        end
    endtask

    initial begin
        for (mode = 0; mode < 3; mode++) begin
            @(negedge clk);
            reset = 1;
            repeat (20) @(negedge clk);
            reset = 0;
            repeat (20) @(negedge clk);
            program_mode(mode);
            repeat (4) @(negedge vblank);
            for (offset_index = 0; offset_index < 2; offset_index++) begin
                h_offset = offset_index == 0 ? 0 : 6;
                repeat (100) @(negedge clk_video);
                repeat (3) measure_line();
            end
        end
        $display("AT_VIDEO_WINDOW_TEST_PASS text200=640 text350=640 graphics200=640 offsets=0,6");
        $finish;
    end

    initial begin
        #300000000;
        $fatal(1, "AT video window timeout");
    end
endmodule
