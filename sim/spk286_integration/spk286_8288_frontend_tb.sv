`timescale 1ns/1ps

// Verifies the production bridge-to-8288 phasing without the rest of the
// machine. In particular, passive gaps must terminate each byte transaction
// so an aligned SPK286 word becomes two distinct XT commands.
module spk286_8288_frontend_tb;
    logic clk = 1'b0;
    logic reset = 1'b1;
    always #5 clk = ~clk;

    logic [2:0] phase = 3'd0;
    logic cpu_ce_posedge = 1'b0;
    logic cpu_ce_negedge = 1'b0;
    always_ff @(posedge clk) begin
        if (reset) begin
            phase <= 3'd0;
            cpu_ce_posedge <= 1'b0;
            cpu_ce_negedge <= 1'b0;
        end else begin
            cpu_ce_posedge <= (phase == 3'd0);
            cpu_ce_negedge <= (phase == 3'd4);
            phase <= phase + 3'd1;
        end
    end

    logic cpu_bus_valid = 1'b0;
    logic [23:0] cpu_address = 24'd0;
    logic [15:0] cpu_data_out = 16'd0;
    logic cpu_data_oe = 1'b0;
    logic cpu_bus_write = 1'b0;
    logic cpu_bus_bhe_n = 1'b1;
    logic [3:0] cpu_bus_status = 4'hf;
    logic cpu_bus_lock = 1'b0;
    wire cpu_ready;
    wire [15:0] cpu_data_in;

    wire xt_valid;
    wire [19:0] xt_address;
    wire [7:0] xt_data_out;
    wire [2:0] xt_status;
    wire xt_write, xt_io, xt_inta, xt_code, xt_byte_high;
    wire xt_memory_projection, xt_lock_n, bridge_idle, protocol_error;
    logic [7:0] xt_data_in;

    logic pic_chip_select_n = 1'b1;
    logic pic_read_enable_n = 1'b1;
    logic pic_write_enable_n = 1'b1;
    logic pic_address = 1'b0;
    logic [7:0] pic_data_in = 8'h00;
    logic [7:0] interrupt_request = 8'h00;
    wire [7:0] pic_data_out;
    wire pic_data_io;
    wire pic_interrupt;

    wire enable_io_command;
    wire advanced_io_write_command_n;
    wire io_write_command_n;
    wire io_read_command_n;
    wire interrupt_acknowledge_n;
    wire enable_memory_command;
    wire advanced_memory_write_command_n;
    wire memory_write_command_n;
    wire memory_read_command_n;
    wire direction_transmit_or_receive_n;
    wire data_enable;
    wire master_cascade_enable;
    wire peripheral_data_enable_n;
    wire address_latch_enable;
    wire [2:0] processor_status = xt_valid ? xt_status : 3'b111;
    wire cycle_active = ~advanced_io_write_command_n |
                        ~io_read_command_n |
                        ~interrupt_acknowledge_n |
                        ~advanced_memory_write_command_n |
                        ~memory_read_command_n;
    integer inta_wait = 0;
    wire xt_ready = cycle_active && (!xt_inta || inta_wait >= 2);

    integer accepted_beats = 0;
    integer command_starts = 0;
    integer address_latches = 0;
    logic cycle_active_q = 1'b0;
    logic [19:0] latched_address = 20'd0;
    logic [7:0] accepted_data [0:7];
    logic [19:0] accepted_address [0:7];

    always_comb begin
        if (xt_inta)
            xt_data_in = pic_data_out;
        else begin
            case (xt_address[1:0])
                2'd0: xt_data_in = 8'h5a;
                2'd1: xt_data_in = 8'ha5;
                2'd2: xt_data_in = 8'h3c;
                default: xt_data_in = 8'hc3;
            endcase
        end
    end

    always_ff @(posedge clk) begin
        if (reset || !cycle_active || !xt_inta)
            inta_wait <= 0;
        else if (inta_wait < 3)
            inta_wait <= inta_wait + 1;
        cycle_active_q <= cycle_active;
        if (cycle_active && !cycle_active_q)
            command_starts <= command_starts + 1;
        if (address_latch_enable) begin
            latched_address <= xt_address;
            address_latches <= address_latches + 1;
        end
        if (!reset && xt_valid && cycle_active && xt_ready) begin
            accepted_address[accepted_beats] <= xt_address;
            accepted_data[accepted_beats] <= xt_data_out;
            accepted_beats <= accepted_beats + 1;
            if (latched_address != xt_address && !address_latch_enable)
                $fatal(1, "8288 command used an address that was not latched");
        end
    end

    task automatic write_pic(input logic port_address,
                             input logic [7:0] value);
        begin
            @(negedge clk);
            pic_chip_select_n = 1'b0;
            pic_write_enable_n = 1'b0;
            pic_address = port_address;
            pic_data_in = value;
            @(negedge clk);
            pic_chip_select_n = 1'b1;
            pic_write_enable_n = 1'b1;
            pic_address = 1'b0;
            pic_data_in = 8'h00;
        end
    endtask

    task automatic request(
        input logic [23:0] address_value,
        input logic [3:0] status_value,
        input logic write_value,
        input logic bhe_n_value,
        input logic [15:0] data_value,
        output logic [15:0] response
    );
        integer deadline;
        begin
            @(negedge clk);
            cpu_address = address_value;
            cpu_bus_status = status_value;
            cpu_bus_write = write_value;
            cpu_data_oe = write_value;
            cpu_bus_bhe_n = bhe_n_value;
            cpu_data_out = data_value;
            cpu_bus_valid = 1'b1;
            for (deadline = 0; deadline < 1000 && !cpu_ready; deadline = deadline + 1)
                @(negedge clk);
            if (!cpu_ready)
                $fatal(1, "8288 frontend request timed out status=%h", status_value);
            response = cpu_data_in;
            cpu_bus_valid = 1'b0;
            @(negedge clk);
        end
    endtask

    spk286_xt_bridge bridge (
        .clk(clk), .reset(reset),
        .cpu_bus_valid(cpu_bus_valid), .cpu_address(cpu_address),
        .cpu_data_out(cpu_data_out), .cpu_data_oe(cpu_data_oe),
        .cpu_bus_write(cpu_bus_write), .cpu_bus_bhe_n(cpu_bus_bhe_n),
        .cpu_bus_status(cpu_bus_status), .cpu_bus_lock(cpu_bus_lock),
        .cpu_ready(cpu_ready), .cpu_data_in(cpu_data_in),
        .xt_start(cpu_ce_posedge), .xt_cycle_active(cycle_active),
        .xt_ready(xt_ready), .xt_data_in(xt_data_in),
        .xt_valid(xt_valid), .xt_address(xt_address),
        .xt_data_out(xt_data_out), .xt_status(xt_status),
        .xt_write(xt_write), .xt_io(xt_io), .xt_inta(xt_inta),
        .xt_code(xt_code), .xt_byte_high(xt_byte_high),
        .xt_memory_projection(xt_memory_projection), .xt_lock_n(xt_lock_n),
        .bridge_idle(bridge_idle), .protocol_error(protocol_error)
    );

    KF8288 controller (
        .clock(clk), .cpu_ce_posedge(cpu_ce_posedge),
        .cpu_ce_negedge(cpu_ce_negedge), .reset(reset),
        .address_enable_n(1'b0), .command_enable(1'b1),
        .io_bus_mode(1'b0), .processor_status(processor_status),
        .enable_io_command(enable_io_command),
        .advanced_io_write_command_n(advanced_io_write_command_n),
        .io_write_command_n(io_write_command_n),
        .io_read_command_n(io_read_command_n),
        .interrupt_acknowledge_n(interrupt_acknowledge_n),
        .enable_memory_command(enable_memory_command),
        .advanced_memory_write_command_n(advanced_memory_write_command_n),
        .memory_write_command_n(memory_write_command_n),
        .memory_read_command_n(memory_read_command_n),
        .direction_transmit_or_receive_n(direction_transmit_or_receive_n),
        .data_enable(data_enable),
        .master_cascade_enable(master_cascade_enable),
        .peripheral_data_enable_n(peripheral_data_enable_n),
        .address_latch_enable(address_latch_enable)
    );

`ifdef I4_PIC_MODEL
    spk286_pic_model pic (
`else
    KF8259 pic (
`endif
        .clock(clk), .reset(reset),
        .chip_select_n(pic_chip_select_n),
        .read_enable_n(pic_read_enable_n),
        .write_enable_n(pic_write_enable_n),
        .address(pic_address), .data_bus_in(pic_data_in),
        .data_bus_out(pic_data_out), .data_bus_io(pic_data_io),
        .cascade_in(3'b000), .cascade_out(), .cascade_io(),
        .slave_program_n(1'b1), .buffer_enable(),
        .slave_program_or_enable_buffer(),
        .interrupt_acknowledge_n(interrupt_acknowledge_n),
        .interrupt_to_cpu(pic_interrupt),
        .interrupt_request(interrupt_request)
    );

    initial begin : test
        logic [15:0] response;
        integer before_beats;
        integer before_commands;
        repeat (5) @(posedge clk);
        reset = 1'b0;

        before_beats = accepted_beats;
        before_commands = command_starts;
        request(24'h0f0100, 4'hd, 1'b0, 1'b1, 16'd0, response);
        if (response !== 16'h005a || accepted_beats != before_beats + 1 ||
            command_starts != before_commands + 1)
            $fatal(1, "CODE read did not form one 8288 command");

        before_beats = accepted_beats;
        before_commands = command_starts;
        request(24'h000200, 4'h6, 1'b1, 1'b0, 16'ha55a, response);
        if (accepted_beats != before_beats + 2 ||
            command_starts != before_commands + 2 ||
            accepted_address[before_beats] !== 20'h00200 ||
            accepted_address[before_beats + 1] !== 20'h00201 ||
            accepted_data[before_beats] !== 8'h5a ||
            accepted_data[before_beats + 1] !== 8'ha5)
            $fatal(1, "word write was not two distinct 8288 commands");

        before_beats = accepted_beats;
        before_commands = command_starts;
        write_pic(1'b0, 8'h13);
        write_pic(1'b1, 8'h20);
        write_pic(1'b1, 8'h01);
        write_pic(1'b1, 8'hfe);
        interrupt_request = 8'h01;
        repeat (4) @(negedge clk);
        if (!pic_interrupt)
            $fatal(1, "programmed PIC did not present IRQ0");
        request(24'd0, 4'h0, 1'b0, 1'b1, 16'd0, response);
        interrupt_request = 8'h00;
        request(24'd0, 4'h0, 1'b0, 1'b1, 16'd0, response);
        if (accepted_beats != before_beats + 2 ||
            command_starts != before_commands + 2 || response !== 16'h0020)
            $fatal(1, "two 8288/PIC INTA commands did not return vector 20h");
        if (protocol_error || address_latches < accepted_beats)
            $fatal(1, "8288 frontend protocol/latch observation failed");

        $display("I4_8288_FRONTEND_PASS beats=%0d commands=%0d address_latches=%0d",
                 accepted_beats, command_starts, address_latches);
        $finish;
    end
endmodule
