`timescale 1ns/1ps

module pcat_rom_loader_tb;
    logic clock = 1'b0;
    logic reset = 1'b1;
    logic sdram_initialized = 1'b0;
    logic [1:0] rom_protect = 2'b00;
    logic processor_ready = 1'b0;
    logic address_direction = 1'b1;
    logic ioctl_download = 1'b0;
    logic [7:0] ioctl_index = 8'h00;
    logic ioctl_wr = 1'b0;
    logic [24:0] ioctl_addr = 25'd0;
    logic [15:0] ioctl_data = 16'd0;
    wire ioctl_wait;
    wire [2:0] bios_protect_flag;
    wire bios_access_request;
    wire [19:0] bios_access_address;
    wire [15:0] bios_write_data;
    wire bios_write_n;
    wire [7:0] bios_write_wait_count;
    wire bios_write_byte_count;
    wire [4:0] bios_load_state;
    wire main_rom_loaded;
    wire ega_rom_loaded;
    wire ega_rom_write_protect;
    wire [1:0] ega_video_switches;

    logic [7:0] main_memory [0:65535];
    integer main_writes = 0;
    integer ega_writes = 0;
    logic previous_write_n = 1'b1;
    integer index;

    wire bios_missing_main = !main_rom_loaded;
    wire bios_missing_ega = main_rom_loaded && !ega_rom_loaded;
    wire bios_hold;

    always #5 clock = ~clock;

    pcat_rom_loader dut (.*);

    bios_hold_notice #(.INFO_PERIOD(25'd16), .INFO_WIDTH(25'd4)) hold_gate (
        .clock(clock),
        .splash_boot_phase(1'b0),
        .bios_missing_pcxt(bios_missing_main),
        .bios_missing_ega(bios_missing_ega),
        .hold(bios_hold),
        .info(),
        .info_req()
    );

    always_ff @(posedge clock) begin
        previous_write_n <= bios_write_n;
        if (!reset && previous_write_n && !bios_write_n) begin
            if (!bios_access_request)
                $fatal(1, "ROM write occurred without loader ownership");
            if (bios_access_address >= 20'hf0000) begin
                main_memory[bios_access_address[15:0]] <= bios_write_data[7:0];
                if (bios_access_address != 20'hf0000 + main_writes)
                    $fatal(1, "main ROM address sequence mismatch at write %0d: %h",
                           main_writes, bios_access_address);
                main_writes <= main_writes + 1;
            end else if (bios_access_address == (20'hc0000 + ega_writes))
                ega_writes <= ega_writes + 1;
            else
                $fatal(1, "unexpected ROM loader address %h", bios_access_address);
        end
    end

    function automatic logic [15:0] diagnostic_word(input integer word_index);
        diagnostic_word = {word_index[15:8] ^ 8'h5a,
                           word_index[7:0] ^ 8'ha5};
    endfunction

    task automatic send_word(input logic [24:0] byte_offset,
                             input logic [15:0] value);
        integer deadline;
        begin
            for (deadline = 0;
                 deadline < 400 && !(bios_load_state == 5'h01 && !ioctl_wait);
                 deadline = deadline + 1)
                @(negedge clock);
            if (deadline == 400)
                $fatal(1, "loader did not request the next input word");
            ioctl_addr = byte_offset;
            ioctl_data = value;
            ioctl_wr = 1'b1;
            for (deadline = 0;
                 deadline < 40 && bios_load_state != 5'h02;
                 deadline = deadline + 1)
                @(negedge clock);
            if (deadline == 40)
                $fatal(1, "loader did not accept input word at %h", byte_offset);
            ioctl_wr = 1'b0;
            for (deadline = 0;
                 deadline < 400 && !(bios_load_state == 5'h01 && !ioctl_wait);
                 deadline = deadline + 1)
                @(negedge clock);
            if (deadline == 400)
                $fatal(1, "loader did not complete input word at %h", byte_offset);
        end
    endtask

    initial begin
        for (index = 0; index < 65536; index = index + 1)
            main_memory[index] = 8'hcc;

        repeat (4) @(posedge clock);
        reset = 1'b0;
        sdram_initialized = 1'b1;
        repeat (4) @(posedge clock);
        if (!bios_hold || main_rom_loaded || ega_rom_loaded)
            $fatal(1, "missing ROMs did not retain the reset hold");

        // Send every word of the 64 KiB diagnostic slot. This verifies both
        // WIDE=1 bytes, the F0000h base and the FFFFFh last byte dynamically.
        ioctl_index = 8'h00;
        ioctl_download = 1'b1;
        for (index = 0; index < 32768; index = index + 1)
            send_word(index * 2, diagnostic_word(index));
        ioctl_download = 1'b0;
        repeat (6) @(posedge clock);

        if (!main_rom_loaded || main_writes != 65536)
            $fatal(1, "main ROM load incomplete loaded=%b writes=%0d",
                   main_rom_loaded, main_writes);
        if (main_memory[16'h0000] !== 8'ha5 ||
            main_memory[16'h0001] !== 8'h5a ||
            main_memory[16'h2468] !== (8'h34 ^ 8'ha5) ||
            main_memory[16'h2469] !== (8'h12 ^ 8'h5a) ||
            main_memory[16'hfffe] !== (8'hff ^ 8'ha5) ||
            main_memory[16'hffff] !== (8'h7f ^ 8'h5a))
            $fatal(1, "main ROM data content mismatch");
        if (!bios_hold || !bios_missing_ega)
            $fatal(1, "reset hold did not advance to missing EGA ROM");

        // One EGA word is sufficient to exercise its distinct C0000h mapping
        // and presence gate; image content/licensing remains external.
        ioctl_index = 8'h03;
        ioctl_download = 1'b1;
        send_word(25'd0, 16'haa55);
        ioctl_download = 1'b0;
        repeat (6) @(posedge clock);
        if (!ega_rom_loaded || !ega_rom_write_protect ||
            ega_video_switches != 2'b00 || ega_writes != 2)
            $fatal(1, "EGA ROM presence/mapping mismatch");
        if (bios_hold)
            $fatal(1, "both loaded ROMs did not release the machine hold");

        // SDRAM loss invalidates both presence flags and returns to a protected
        // idle state rather than releasing stale ROM contents.
        sdram_initialized = 1'b0;
        @(posedge clock);
        #1;
        if (main_rom_loaded || ega_rom_loaded || !bios_write_n ||
            bios_access_request || bios_protect_flag != 3'b011)
            $fatal(1, "SDRAM reset did not invalidate the loader");

        $display("I4_ROM_LOADER_PASS main_bytes=%0d ega_bytes=%0d first=%h last=%h",
                 main_writes, ega_writes, main_memory[0], main_memory[65535]);
        $finish;
    end

    initial begin
        #200000000;
        $fatal(1, "ROM loader test timeout state=%h writes=%0d",
               bios_load_state, main_writes);
    end
endmodule
