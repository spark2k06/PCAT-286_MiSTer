`timescale 1ns/1ps

// I4 regression for the copied machine arbiter's explicit SPK286 HOLD/HLDA
// contract. The real controller implementations are replaced with narrow pin
// observers; address ownership and grant timing remain the production logic.
module spk286_bus_ownership_tb;
    logic         clock = 1'b0;
    logic         reset = 1'b1;
    logic         cpu_ce_posedge = 1'b0;
    logic         cpu_ce_negedge = 1'b0;
    logic [19:0]  cpu_address = '0;
    logic [7:0]   cpu_data_bus = '0;
    logic [2:0]   processor_status = 3'b111;
    logic         processor_lock_n = 1'b1;
    logic         processor_hold_acknowledge = 1'b0;
    logic         dma_ready = 1'b1;
    logic         dma_chip_select_n = 1'b1;
    logic         dma_page_chip_select_n = 1'b1;
    logic [19:0]  address_ext = '0;
    logic [7:0]   data_bus_ext = '0;
    logic         io_read_n_ext = 1'b1;
    logic         io_write_n_ext = 1'b1;
    logic         memory_read_n_ext = 1'b1;
    logic         memory_write_n_ext = 1'b1;
    logic         ext_access_request = 1'b0;
    logic [3:0]   dma_request = 4'b0000;

    wire          processor_transmit_or_receive_n;
    wire          processor_hold_request;
    wire          dma_wait_n;
    wire          interrupt_acknowledge_n;
    wire [19:0]   address;
    wire          address_direction;
    wire [7:0]    internal_data_bus;
    wire          data_bus_direction;
    wire          address_latch_enable;
    wire          io_read_n;
    wire          io_read_n_direction;
    wire          io_write_n;
    wire          io_write_n_direction;
    wire          memory_read_n;
    wire          memory_read_n_direction;
    wire          memory_write_n;
    wire          memory_write_n_direction;
    wire          no_command_state;
    wire [3:0]    dma_acknowledge_n;
    wire          address_enable_n;
    wire          terminal_count_n;

    always #5 clock = ~clock;

    BUS_ARBITER dut (.*);

    task automatic cpu_edge(input logic positive_edge);
        begin
            @(negedge clock);
            cpu_ce_posedge = positive_edge;
            cpu_ce_negedge = ~positive_edge;
            @(posedge clock);
            #1;
            cpu_ce_posedge = 1'b0;
            cpu_ce_negedge = 1'b0;
        end
    endtask

    initial begin
        integer checks;
        checks = 0;
        repeat (3) @(posedge clock);

        // Reset-held loading owns the external bus immediately. Waiting for
        // HLDA here would deadlock because the CPU is held in reset.
        if (!address_enable_n || !address_direction)
            $fatal(1, "reset-held loader did not own the external bus");
        checks = checks + 1;

        reset = 1'b0;
        cpu_edge(1'b1);
        if (address_enable_n)
            $fatal(1, "CPU did not recover ownership after reset");
        checks = checks + 1;

        // A runtime loader request reaches HOLD but cannot own the bus until
        // qualified HLDA is returned by the top-level.
        address_ext = 20'hf1234;
        ext_access_request = 1'b1;
        #1;
        if (!processor_hold_request)
            $fatal(1, "runtime external request did not assert HOLD");
        cpu_edge(1'b1);
        if (address_enable_n)
            $fatal(1, "runtime loader was granted before HLDA");
        checks = checks + 2;

        processor_hold_acknowledge = 1'b1;
        cpu_edge(1'b1);
        if (!address_enable_n || !address_direction || address != address_ext)
            $fatal(1, "qualified HLDA did not grant the runtime loader");
        checks = checks + 1;

        ext_access_request = 1'b0;
        processor_hold_acknowledge = 1'b0;
        cpu_edge(1'b1);
        if (address_enable_n)
            $fatal(1, "CPU ownership did not return after loader request");
        checks = checks + 1;

        // The 8237 request follows the same real handshake.
        dma_request[0] = 1'b1;
        #1;
        if (!processor_hold_request)
            $fatal(1, "DMA request did not assert HOLD");
        cpu_edge(1'b1);
        if (address_enable_n)
            $fatal(1, "DMA was granted before HLDA");
        processor_hold_acknowledge = 1'b1;
        cpu_edge(1'b1);
        cpu_edge(1'b0);
        if (!address_enable_n ||
            !dut.u_KF8237.saw_ack_on_first_negedge)
            $fatal(1, "qualified DMA grant did not reach the 8237");
        checks = checks + 3;

        // A disappearing request releases the bus on the next safe phase.
        dma_request[0] = 1'b0;
        processor_hold_acknowledge = 1'b0;
        cpu_edge(1'b1);
        if (address_enable_n || processor_hold_request)
            $fatal(1, "disappearing DMA request retained ownership");
        checks = checks + 1;

        // Reset during an arbitrary CPU-owned interval cancels the runtime
        // grant state and restores the separate loader owner.
        reset = 1'b1;
        @(posedge clock);
        #1;
        if (!address_enable_n || !address_direction)
            $fatal(1, "reset did not restore loader ownership");
        checks = checks + 1;
        reset = 1'b0;
        cpu_edge(1'b1);
        if (address_enable_n)
            $fatal(1, "post-reset CPU ownership did not recover");
        checks = checks + 1;

        $display("I4_BUS_OWNERSHIP_PASS checks=%0d", checks);
        $finish;
    end
endmodule

// Minimal 8288 pin stub used only by this unit test.
module KF8288 (
    input  logic clock, cpu_ce_posedge, cpu_ce_negedge, reset,
    input  logic address_enable_n, command_enable, io_bus_mode,
    input  logic [2:0] processor_status,
    output logic enable_io_command, advanced_io_write_command_n,
    output logic io_read_command_n, interrupt_acknowledge_n,
    output logic enable_memory_command, advanced_memory_write_command_n,
    output logic memory_read_command_n, direction_transmit_or_receive_n,
    output logic data_enable, address_latch_enable
);
    always_comb begin
        enable_io_command = 1'b0;
        advanced_io_write_command_n = 1'b1;
        io_read_command_n = 1'b1;
        interrupt_acknowledge_n = 1'b1;
        enable_memory_command = 1'b0;
        advanced_memory_write_command_n = 1'b1;
        memory_read_command_n = 1'b1;
        direction_transmit_or_receive_n = 1'b1;
        data_enable = 1'b0;
        address_latch_enable = 1'b0;
    end
endmodule

// Minimal 8237 pin stub.  DREQ directly raises HRQ and the observer samples
// HLDA exactly as the real controller does on cpu_ce_negedge.
module KF8237 (
    input  logic clock, cpu_ce_posedge, cpu_ce_negedge, reset,
    input  logic chip_select_n, ready, hold_acknowledge,
    input  logic [3:0] dma_request,
    input  logic [7:0] data_bus_in,
    output logic [7:0] data_bus_out,
    input  logic io_read_n_in,
    output logic io_read_n_out, io_read_n_io,
    input  logic io_write_n_in,
    output logic io_write_n_out, io_write_n_io,
    input  logic end_of_process_n_in,
    output logic end_of_process_n_out,
    input  logic [3:0] address_in,
    output logic [15:0] address_out,
    output logic output_highst_address, hold_request,
    output logic [3:0] dma_acknowledge,
    output logic address_enable, address_strobe,
    output logic memory_read_n, memory_write_n
);
    logic saw_ack_on_first_negedge = 1'b0;
    logic first_negedge_pending = 1'b0;

    assign hold_request = |dma_request;

    always_ff @(posedge clock) begin
        if (reset) begin
            first_negedge_pending <= 1'b0;
            saw_ack_on_first_negedge <= 1'b0;
        end else begin
            if (cpu_ce_posedge && hold_request)
                first_negedge_pending <= 1'b1;
            if (cpu_ce_negedge && first_negedge_pending) begin
                saw_ack_on_first_negedge <= hold_acknowledge;
                first_negedge_pending <= 1'b0;
            end
        end
    end

    always_comb begin
        data_bus_out = '0;
        io_read_n_out = 1'b1;
        io_read_n_io = 1'b1;
        io_write_n_out = 1'b1;
        io_write_n_io = 1'b1;
        end_of_process_n_out = 1'b1;
        address_out = '0;
        output_highst_address = 1'b0;
        dma_acknowledge = 4'b1111;
        address_enable = 1'b0;
        address_strobe = 1'b0;
        memory_read_n = 1'b1;
        memory_write_n = 1'b1;
    end
endmodule
