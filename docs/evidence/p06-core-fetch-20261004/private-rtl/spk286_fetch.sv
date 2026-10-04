// One outstanding fetch and one response slot for the future six-byte prefetch.
// Transaction semantics only: native 80286 Ts/Tc timing is not implemented yet.
`timescale 1ns/1ps

module spk286_fetch #(parameter bit P06_FETCH_TIMING = 1'b0) (
    // Timing-only inputs deliberately disappear in MAX.
    /* verilator lint_off UNUSEDSIGNAL */
    input logic p06_cpu_boundary, p06_board_ready, p06_admission_enable,
    /* verilator lint_on UNUSEDSIGNAL */
    input  logic        clk,
    input  logic        reset,
    input  logic        ready,
    input  logic [15:0] data_in,
    input  logic [23:0] code_base,
    input  logic [15:0] code_limit,
    input  logic        wrap_ip,
    input  logic        restart,
    input  logic [15:0] restart_ip,
    input  logic        request,
    input  logic        suspend,
    output logic        request_ready,
    input  logic        response_ready,
    output logic        response_valid,
    output logic [15:0] response_data,
    output logic [15:0] response_ip,
    output logic [1:0]  response_count,
    output logic [16:0] cursor,
    output logic        blocked,
    output logic        bus_valid,
    output logic        bus_bhe_n,
    output logic [23:0] address
);
    logic active_q, canceled_q, restart_pending_q;
    logic [16:0] cursor_q;
    logic [23:0] address_q;
    logic [15:0] request_ip_q;
    logic [1:0] request_count_q;
    logic bhe_n_q;
    logic [23:0] next_address;
    logic single_byte;
    localparam logic FETCH_CHAINING = 1'b1;
    wire response_fire = response_valid && response_ready;
    wire response_slot_available = !raw_response_valid ||
                                   (FETCH_CHAINING && response_fire);

// Inserted into the private original fetch by build_p06_fetch_cpu.py.
// Physical READY capture uses the ORIGINAL result slot on every fabric edge.
// Only logical issue/publication and availability are temporally qualified.
    logic raw_response_valid;
    logic [15:0] raw_response_data, raw_response_ip;
    logic [1:0] raw_response_count;
    logic p06_admit, p06_can_issue;
    // Hierarchical timing diagnostics are intentionally pruned in MAX.
    /* verilator lint_off UNUSEDSIGNAL */
    logic p06_issue, p06_capture, p06_complete;
    /* verilator lint_on UNUSEDSIGNAL */
    assign p06_capture = !reset && active_q && ready;
    assign p06_can_issue = !suspend &&
        response_slot_available && !blocked && (restart_pending_q || request) && p06_admit;
    assign p06_issue = !reset && !restart && !active_q && p06_can_issue;
    generate
        if (P06_FETCH_TIMING) begin : p06_historical
            localparam logic [1:0] IDLE = 0, TS = 1, TC = 2, PUBLISHED = 3;
            logic [1:0] state_q;
            wire available = raw_response_valid || p06_capture;
            wire sample_tc = !reset && !restart && !canceled_q &&
                p06_cpu_boundary && state_q == TC;
            /* verilator lint_off UNUSEDSIGNAL */
            wire external_wait = sample_tc && !p06_board_ready;
            wire deadline_miss = sample_tc && p06_board_ready && !available;
            /* verilator lint_on UNUSEDSIGNAL */
            assign p06_complete = sample_tc && p06_board_ready && available;
            assign response_valid = !reset && !restart &&
                ((state_q == PUBLISHED && raw_response_valid) || p06_complete);
            // Same-edge physical READY at Tc has an explicit data/metadata bypass.
            // A poisoned data_in after an earlier READY cannot change retention.
            assign response_data = !raw_response_valid && p06_capture ?
                (request_count_q == 2 ? data_in :
                    (address_q[0] ? {8'd0, data_in[15:8]} : {8'd0, data_in[7:0]})) : raw_response_data;
            assign response_ip = !raw_response_valid && p06_capture ? request_ip_q : raw_response_ip;
            assign response_count = !raw_response_valid && p06_capture ? request_count_q : raw_response_count;
            assign p06_admit = !reset && !restart && p06_cpu_boundary && p06_admission_enable &&
                (state_q == IDLE || ((p06_complete || state_q == PUBLISHED) && response_fire));
            always_ff @(posedge clk) begin
                if (reset || restart) state_q <= IDLE;
                else begin
                    if (state_q == TS && p06_cpu_boundary) state_q <= TC;
                    if (p06_complete) state_q <= response_ready ? IDLE : PUBLISHED;
                    if (state_q == PUBLISHED && response_fire) state_q <= IDLE;
                    // No Ti bubble when a reserved next fetch is admitted at Tc.
                    if (p06_issue) state_q <= TS;
                end
            end
        end else begin : p06_maximum
            assign response_valid = raw_response_valid;
            assign response_data = raw_response_data;
            assign response_ip = raw_response_ip;
            assign response_count = raw_response_count;
            assign p06_admit = 1'b1;
            assign p06_complete = 1'b0;
        end
    endgenerate

    assign cursor = cursor_q;
    assign blocked = (cursor_q[16] && !wrap_ip) || (cursor_q[15:0] > code_limit);
    assign next_address = code_base + {8'h00, cursor_q[15:0]};
    assign single_byte = next_address[0] || (cursor_q[15:0] == code_limit);
    assign request_ready = !reset && !restart && !restart_pending_q &&
                           !active_q && response_slot_available && !blocked && p06_admit;
    assign bus_valid = active_q && !reset;
    assign address = bus_valid ? address_q : 24'h000000;
    assign bus_bhe_n = bus_valid ? bhe_n_q : 1'b1;

    always_ff @(posedge clk) begin
        if (reset) begin
            active_q <= 1'b0;
            canceled_q <= 1'b0;
            restart_pending_q <= 1'b1;
            cursor_q <= 17'h0FFF0;
            address_q <= 24'h000000;
            request_ip_q <= 16'h0000;
            request_count_q <= 2'd0;
            bhe_n_q <= 1'b1;
            raw_response_valid <= 1'b0;
            raw_response_data <= 16'h0000;
            raw_response_ip <= 16'h0000;
            raw_response_count <= 2'd0;
        end else if (restart) begin
            // The new architectural CS cache is available on the following edge.
            cursor_q <= {1'b0, restart_ip};
            restart_pending_q <= 1'b1;
            raw_response_valid <= 1'b0;
            if (active_q && !ready) canceled_q <= 1'b1;
            else begin
                active_q <= 1'b0;
                canceled_q <= 1'b0;
            end
        end else begin
            if (response_fire) raw_response_valid <= 1'b0;
            if (active_q) begin
                if (ready) begin
                    active_q <= 1'b0;
                    canceled_q <= 1'b0;
                    if (!canceled_q) begin
                        raw_response_valid <= !(P06_FETCH_TIMING && response_fire);
                        raw_response_ip <= request_ip_q;
                        raw_response_count <= request_count_q;
                        if (request_count_q == 2'd2) raw_response_data <= data_in;
                        else if (address_q[0]) raw_response_data <= {8'h00, data_in[15:8]};
                        else raw_response_data <= {8'h00, data_in[7:0]};
                        // Real-mode IP is a 16-bit register and wraps after FFFF.
                        // Protected fetches retain the 17th bit so an over-limit
                        // stream is reported instead of silently restarting.
                        if (wrap_ip)
                            cursor_q <= {1'b0, request_ip_q + {14'h0000, request_count_q}};
                        else
                            cursor_q <= {1'b0, request_ip_q} + {15'h0000, request_count_q};
                    end
                end
            end else if (p06_can_issue) begin
                // P02 may retire the response and capture the next fetch on
                // the same edge; the base profile keeps the old bubble.
                active_q <= 1'b1;
                canceled_q <= 1'b0;
                restart_pending_q <= 1'b0;
                address_q <= next_address;
                request_ip_q <= cursor_q[15:0];
                request_count_q <= single_byte ? 2'd1 : 2'd2;
                bhe_n_q <= single_byte && !next_address[0];
            end
        end
    end
endmodule
