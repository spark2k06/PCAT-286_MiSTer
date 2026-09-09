`timescale 1ns/1ps

module spk286_xt_bridge_tb #(
    parameter integer MUTATION = 0
);
    logic clk = 1'b0;
    logic reset = 1'b1;

    logic cpu_bus_valid = 1'b0;
    logic [23:0] cpu_address = 24'd0;
    logic [15:0] cpu_data_out = 16'd0;
    logic cpu_data_oe = 1'b0;
    logic cpu_bus_write = 1'b0;
    logic cpu_bus_bhe_n = 1'b1;
    logic [3:0] cpu_bus_status = 4'hf;
    logic cpu_bus_lock = 1'b0;
    logic cpu_ready;
    logic [15:0] cpu_data_in;

    logic xt_start = 1'b1;
    logic backend_cycle_enable = 1'b1;
    logic backend_ready = 1'b0;
    logic [7:0] backend_data = 8'd0;
    logic address_data_mode = 1'b0;
    logic stale_phase = 1'b0;
    logic xt_cycle_active;
    logic xt_ready;
    logic [7:0] xt_data_in;
    logic xt_valid;
    logic [19:0] xt_address;
    logic [7:0] xt_data_out;
    logic [2:0] xt_status;
    logic xt_write, xt_io, xt_inta, xt_code, xt_byte_high;
    logic xt_memory_projection, xt_lock_n, bridge_idle, protocol_error;

    logic external_request = 1'b0;
    logic loader_reset_owner = 1'b0;
    logic cpu_hlda = 1'b0;
    logic owner_cpu_lock = 1'b0;
    logic owner_bridge_idle = 1'b1;
    logic cpu_hold_request;
    logic external_grant;

    integer accepted_beats = 0;
    integer port_write_effects = 0;
    integer inta_accepted = 0;
    integer inta_effects = 0;

    wire [2:0] checked_status =
        ((MUTATION == 1) && xt_code) ? 3'b101 : xt_status;
    wire [7:0] checked_data_out =
        ((MUTATION == 2) && xt_byte_high) ? {xt_data_out[3:0], xt_data_out[7:4]} : xt_data_out;
    wire checked_cpu_ready = cpu_ready ||
        ((MUTATION == 3) && xt_valid && !xt_byte_high);
    wire checked_external_grant =
        (MUTATION == 7) ? external_request : external_grant;

    always #5 clk = ~clk;
    assign xt_cycle_active = backend_cycle_enable && xt_valid;
    assign xt_ready = backend_ready;

    always_comb begin
        if (address_data_mode)
            xt_data_in = xt_address[0] ? 8'h22 : 8'h11;
        else if ((MUTATION == 5) && stale_phase)
            xt_data_in = 8'h31;
        else
            xt_data_in = backend_data;
    end

    always @(posedge clk) begin
        if (!reset && xt_valid && xt_cycle_active && xt_ready) begin
            accepted_beats <= accepted_beats + 1;
            if (xt_io && xt_write)
                port_write_effects <= port_write_effects +
                                      ((MUTATION == 4) ? 2 : 1);
            if (xt_inta) begin
                inta_accepted <= inta_accepted + 1;
                if (!((MUTATION == 6) && (inta_accepted == 1)))
                    inta_effects <= inta_effects + 1;
            end
        end
    end

    spk286_xt_bridge dut (
        .clk(clk), .reset(reset),
        .cpu_bus_valid(cpu_bus_valid), .cpu_address(cpu_address),
        .cpu_data_out(cpu_data_out), .cpu_data_oe(cpu_data_oe),
        .cpu_bus_write(cpu_bus_write), .cpu_bus_bhe_n(cpu_bus_bhe_n),
        .cpu_bus_status(cpu_bus_status), .cpu_bus_lock(cpu_bus_lock),
        .cpu_ready(cpu_ready), .cpu_data_in(cpu_data_in),
        .xt_start(xt_start), .xt_cycle_active(xt_cycle_active),
        .xt_ready(xt_ready), .xt_data_in(xt_data_in),
        .xt_valid(xt_valid), .xt_address(xt_address),
        .xt_data_out(xt_data_out), .xt_status(xt_status),
        .xt_write(xt_write), .xt_io(xt_io), .xt_inta(xt_inta),
        .xt_code(xt_code), .xt_byte_high(xt_byte_high),
        .xt_memory_projection(xt_memory_projection), .xt_lock_n(xt_lock_n),
        .bridge_idle(bridge_idle), .protocol_error(protocol_error)
    );

    spk286_xt_ownership ownership (
        .external_request(external_request),
        .loader_reset_owner(loader_reset_owner),
        .cpu_hlda(cpu_hlda), .cpu_lock(owner_cpu_lock),
        .bridge_idle(owner_bridge_idle),
        .cpu_hold_request(cpu_hold_request),
        .external_grant(external_grant)
    );

    task automatic check(input logic condition, input string message);
        if (!condition)
            $fatal(1, "CHECK_FAIL mutation=%0d: %s", MUTATION, message);
    endtask

    task automatic begin_request(
        input logic [23:0] address_value,
        input logic [3:0] status_value,
        input logic write_value,
        input logic bhe_n_value,
        input logic [15:0] data_value
    );
        @(negedge clk);
        cpu_address = address_value;
        cpu_bus_status = status_value;
        cpu_bus_write = write_value;
        cpu_data_oe = write_value;
        cpu_bus_bhe_n = bhe_n_value;
        cpu_data_out = data_value;
        cpu_bus_valid = 1'b1;
    endtask

    task automatic wait_active;
        integer deadline;
        begin
            for (deadline = 0; deadline < 100 && !xt_valid; deadline = deadline + 1)
                @(negedge clk);
            check(xt_valid, "downstream beat did not start");
        end
    endtask

    task automatic finish_request(output logic [15:0] response);
        integer deadline;
        begin
            for (deadline = 0; deadline < 200 && !cpu_ready; deadline = deadline + 1)
                @(negedge clk);
            check(cpu_ready, "CPU completion did not arrive");
            response = cpu_data_in;
            cpu_bus_valid = 1'b0;
            backend_ready = 1'b0;
            @(negedge clk);
            check(!cpu_ready, "CPU READY was not a single completion interval");
        end
    endtask

    task automatic simple_request(
        input logic [23:0] address_value,
        input logic [3:0] status_value,
        input logic write_value,
        input logic bhe_n_value,
        input logic [15:0] data_value,
        output logic [15:0] response
    );
        begin
            begin_request(address_value, status_value, write_value,
                          bhe_n_value, data_value);
            wait_active();
            backend_ready = 1'b1;
            finish_request(response);
        end
    endtask

    initial begin : run
        logic [15:0] response;
        integer before_count;
        integer first_port_count;

        repeat (4) @(posedge clk);
        reset = 1'b0;

        // CODE must be explicitly translated to 100, never truncated to 101.
        backend_data = 8'hea;
        begin_request(24'hfffff0, 4'hd, 1'b0, 1'b1, 16'd0);
        wait_active();
        check(checked_status == 3'b100, "CODE status was not translated to 100");
        check(xt_address == 20'hffff0, "reset fetch was not projected to XT FFFF0");
        check(xt_memory_projection, "24-bit reset fetch projection was not reported");
        backend_ready = 1'b1;
        finish_request(response);
        check(response == 16'h00ea, "even byte read lane was incorrect");

        // An idle/stale downstream READY is insufficient without an active cycle.
        backend_cycle_enable = 1'b0;
        backend_ready = 1'b1;
        begin_request(24'h000020, 4'h5, 1'b0, 1'b1, 16'd0);
        repeat (6) @(negedge clk);
        check(!cpu_ready, "idle READY completed a transaction");
        backend_cycle_enable = 1'b1;
        finish_request(response);

        // Odd bytes use D15:8 and leave the inactive low byte deterministic.
        backend_data = 8'ha7;
        simple_request(24'h000101, 4'h5, 1'b0, 1'b0, 16'd0, response);
        check(response == 16'ha700, "odd byte read was not positioned in D15:8");

        // An aligned word is two independently mapped byte beats and is only
        // acknowledged after both have completed.
        address_data_mode = 1'b1;
        backend_ready = 1'b0;
        begin_request(24'h000200, 4'h6, 1'b1, 1'b0, 16'ha55a);
        wait_active();
        check(xt_address == 20'h00200 && checked_data_out == 8'h5a,
              "aligned word low beat was incorrect");
        check(!checked_cpu_ready, "word was acknowledged before its first beat");
        backend_ready = 1'b1;
        @(negedge clk);
        backend_ready = 1'b0;
        check(!cpu_ready, "word was acknowledged after only one beat");
        wait_active();
        check(xt_address == 20'h00201 && checked_data_out == 8'ha5,
              "aligned word high beat was incorrect");
        backend_ready = 1'b1;
        finish_request(response);

        backend_ready = 1'b1;
        begin_request(24'h000300, 4'h5, 1'b0, 1'b0, 16'd0);
        wait_active();
        finish_request(response);
        check(response == 16'h2211, "aligned word read assembly was incorrect");
        address_data_mode = 1'b0;

        // I/O retains the port-address carry rather than applying a memory-only
        // alias policy to it.
        backend_data = 8'h44;
        begin_request(24'h010000, 4'h9, 1'b0, 1'b1, 16'd0);
        wait_active();
        check(xt_address == 20'h10000 && !xt_memory_projection,
              "I/O address carry was normalized as memory");
        check(xt_status == 3'b001, "I/O read status mapping was incorrect");
        backend_ready = 1'b1;
        finish_request(response);

        // SPK286 emits an odd word as two retained normalized transfers. Check
        // the exact memory wrap and I/O carry at the XT 20/16-bit boundaries.
        backend_data = 8'hd1;
        begin_request(24'h0fffff, 4'h5, 1'b0, 1'b0, 16'd0);
        wait_active();
        check(xt_address == 20'hfffff && xt_byte_high &&
              !xt_memory_projection,
              "odd memory word first half did not reach FFFFFh");
        backend_ready = 1'b1;
        finish_request(response);
        check(response == 16'hd100,
              "odd memory word first half used the wrong lane");
        backend_data = 8'hd2;
        begin_request(24'h100000, 4'h5, 1'b0, 1'b1, 16'd0);
        wait_active();
        check(xt_address == 20'h00000 && !xt_byte_high &&
              xt_memory_projection,
              "odd memory word second half did not wrap to 00000h");
        backend_ready = 1'b1;
        finish_request(response);
        check(response == 16'h00d2,
              "odd memory word second half used the wrong lane");

        backend_data = 8'he1;
        begin_request(24'h00ffff, 4'h9, 1'b0, 1'b0, 16'd0);
        wait_active();
        check(xt_address == 20'h0ffff && xt_byte_high &&
              !xt_memory_projection,
              "odd I/O word first half did not reach port FFFFh");
        backend_ready = 1'b1;
        finish_request(response);
        backend_data = 8'he2;
        begin_request(24'h010000, 4'h9, 1'b0, 1'b1, 16'd0);
        wait_active();
        check(xt_address == 20'h10000 && !xt_byte_high &&
              !xt_memory_projection,
              "odd I/O word second half lost the port carry");
        backend_ready = 1'b1;
        finish_request(response);

        // One accepted port request produces one physical side effect even if
        // READY remains high.
        before_count = port_write_effects;
        backend_ready = 1'b1;
        simple_request(24'h000080, 4'ha, 1'b1, 1'b1, 16'h0055, response);
        check(port_write_effects == before_count + 1,
              "one port request caused a duplicate or missing write");

        // Identical consecutive requests may keep bus_valid high.
        first_port_count = port_write_effects;
        begin_request(24'h000081, 4'ha, 1'b1, 1'b0, 16'h6600);
        backend_ready = 1'b1;
        while (!cpu_ready) @(negedge clk);
        while (cpu_ready) @(negedge clk);
        while (!cpu_ready) @(negedge clk);
        cpu_bus_valid = 1'b0;
        backend_ready = 1'b0;
        @(negedge clk);
        check(port_write_effects == first_port_count + 2,
              "identical back-to-back port writes were deduplicated or duplicated");

        // Changing input data on repeated reads detects stale INS-style samples.
        backend_data = 8'h31;
        backend_ready = 1'b1;
        simple_request(24'h000060, 4'h9, 1'b0, 1'b1, 16'd0, response);
        check(response == 16'h0031, "first changing input sample was wrong");
        backend_data = 8'h72;
        stale_phase = 1'b1;
        backend_ready = 1'b1;
        simple_request(24'h000060, 4'h9, 1'b0, 1'b1, 16'd0, response);
        check(response == 16'h0072, "second input read reused stale data");
        stale_phase = 1'b0;

        // Two CPU INTA requests remain two separately READY-qualified cycles.
        backend_data = 8'h00;
        backend_ready = 1'b1;
        simple_request(24'd0, 4'h0, 1'b0, 1'b1, 16'd0, response);
        check(response == 16'h0000, "first INTA response was wrong");
        backend_data = 8'h21;
        backend_ready = 1'b1;
        simple_request(24'd0, 4'h0, 1'b0, 1'b1, 16'd0, response);
        check(response == 16'h0021, "second INTA vector response was wrong");
        check(inta_accepted == 2 && inta_effects == 2,
              "two INTA requests did not cause exactly two acknowledgements");

        // LOCK polarity and ownership are explicit. Runtime external ownership
        // is impossible before HLDA and bridge drain; reset-held loading bypasses
        // the CPU handshake.
        cpu_bus_lock = 1'b1;
        @(negedge clk);
        check(!xt_lock_n, "active-high CPU LOCK was not translated to active low");
        cpu_bus_lock = 1'b0;
        external_request = 1'b1;
        #1;
        check(cpu_hold_request, "runtime external request did not reach HOLD");
        check(!checked_external_grant, "external owner was granted before HLDA");
        cpu_hlda = 1'b1;
        #1;
        check(checked_external_grant, "drained HLDA did not grant external owner");
        owner_cpu_lock = 1'b1;
        #1;
        check(!external_grant, "external owner was granted during LOCK");
        owner_cpu_lock = 1'b0;
        owner_bridge_idle = 1'b0;
        #1;
        check(!external_grant, "external owner was granted before bridge drain");
        owner_bridge_idle = 1'b1;
        cpu_hlda = 1'b0;
        loader_reset_owner = 1'b1;
        #1;
        check(external_grant && !cpu_hold_request,
              "reset-held loader incorrectly waited for CPU HLDA");
        external_request = 1'b0;
        loader_reset_owner = 1'b0;

        // Reset during an extended READY stall cancels the retained transfer.
        // A stale completion after release must not replay the old request, and
        // the next independent request must still complete normally.
        before_count = accepted_beats;
        backend_ready = 1'b0;
        begin_request(24'h012340, 4'h5, 1'b0, 1'b1, 16'd0);
        wait_active();
        repeat (8) @(negedge clk);
        check(accepted_beats == before_count,
              "extended READY stall accepted a transfer early");
        reset = 1'b1;
        cpu_bus_valid = 1'b0;
        @(negedge clk);
        check(bridge_idle && !xt_valid && !cpu_ready,
              "reset did not cancel an active retained transfer");
        reset = 1'b0;
        backend_ready = 1'b1;
        repeat (4) @(negedge clk);
        check(accepted_beats == before_count && bridge_idle,
              "stale READY replayed the reset transfer");
        backend_data = 8'h6c;
        simple_request(24'h012341, 4'h5, 1'b0, 1'b0, 16'd0, response);
        check(response == 16'h6c00,
              "bridge did not recover after reset during transfer");

        // No-lane requests are reported and completed without an XT side effect.
        before_count = accepted_beats;
        backend_ready = 1'b1;
        begin_request(24'h000101, 4'h5, 1'b0, 1'b1, 16'd0);
        while (!cpu_ready) @(negedge clk);
        check(protocol_error, "no-lane request did not raise protocol_error");
        check(accepted_beats == before_count,
              "no-lane request fabricated a downstream access");
        cpu_bus_valid = 1'b0;
        backend_ready = 1'b0;
        @(negedge clk);

        check(MUTATION == 0, "fault-injection control unexpectedly survived");
        $display("I2_BRIDGE_PASS beats=%0d port_writes=%0d inta=%0d",
                 accepted_beats, port_write_effects, inta_effects);
        $finish;
    end

    initial begin
        #200000;
        $fatal(1, "CHECK_FAIL mutation=%0d: global timeout", MUTATION);
    end
endmodule
