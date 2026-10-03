// Provisional one-beat logical bus policy, outside the production QIP.
// Packet request/command handshakes are distinct from the current CPU's
// level-held bus_valid interface. The existing bridge is not replaced here.
// Global reset resets the backend too; cancel drains already accepted work.
`timescale 1ns/1ps
module p06_bus_cycle #(
    parameter bit HISTORICAL = 1'b1
) (
    input logic clk, reset, cancel, cpu_boundary, board_ready,
    input logic request_valid,
    output logic request_ready,
    input logic [23:0] request_address,
    input logic [15:0] request_data,
    input logic [1:0] request_lanes,
    input logic [3:0] request_class,
    input logic request_write, request_lock,
    output logic command_valid,
    input logic command_accept,
    output logic [23:0] command_address,
    output logic [15:0] command_data,
    output logic [1:0] command_lanes,
    output logic [3:0] command_class,
    output logic command_write, command_lock,
    input logic completion_valid,
    output logic completion_ready,
    input logic [15:0] completion_data,
    output logic response_valid,
    input logic response_ready,
    output logic [15:0] response_data,
    output logic physical_capture, logical_complete,
    output logic external_wait, deadline_miss,
    output logic busy, draining, protocol_error,
    output logic [1:0] logical_state
);
    generate
        if (HISTORICAL) begin : historical
            localparam logic [1:0] IDLE = 2'd0, TS = 2'd1, TC = 2'd2;
            logic active_q, issued_q, captured_q, published_q, canceled_q;
            logic [1:0] state_q;
            logic [23:0] address_q;
            logic [15:0] data_q, response_q;
            logic [1:0] lanes_q;
            logic [3:0] class_q;
            logic write_q, lock_q;
            wire command_fire = command_valid && command_accept;
            wire result_available = captured_q || physical_capture;
            wire tc_sample = !reset && !cancel && active_q && !canceled_q &&
                             cpu_boundary && (state_q == TC);
            wire response_fire = response_valid && response_ready;
            wire request_fire = request_valid && request_ready;

            assign command_valid = !reset && !cancel && active_q &&
                                   !issued_q && !canceled_q;
            assign command_address = address_q;
            assign command_data = data_q;
            assign command_lanes = lanes_q;
            assign command_class = class_q;
            assign command_write = write_q;
            assign command_lock = lock_q;
            // Capture also during cancellation: accepted operations must drain.
            assign completion_ready = !reset && active_q && !captured_q &&
                                      (issued_q || command_fire);
            assign physical_capture = completion_valid && completion_ready;
            // A same-edge physical result is allowed at an eligible Tc end.
            // No extra implementation extension is hidden as a board wait.
            assign logical_complete = tc_sample && board_ready && result_available;
            assign external_wait = tc_sample && !board_ready;
            assign deadline_miss = tc_sample && board_ready && !result_available;
            assign response_valid = !reset && !cancel &&
                                    (published_q || logical_complete);
            assign response_data = captured_q ? response_q : completion_data;
            assign request_ready = !reset && !cancel && cpu_boundary &&
                ((!active_q && !published_q) ||
                 (logical_complete && response_ready) ||
                 (!active_q && published_q && response_ready));
            assign busy = active_q || published_q;
            assign draining = active_q && canceled_q;
            assign logical_state = state_q;

            always_ff @(posedge clk) begin
                if (reset) begin
                    active_q <= 1'b0; issued_q <= 1'b0;
                    captured_q <= 1'b0; published_q <= 1'b0; canceled_q <= 1'b0;
                    state_q <= IDLE;
                    address_q <= 24'd0; data_q <= 16'd0; response_q <= 16'd0;
                    lanes_q <= 2'd0; class_q <= 4'd0;
                    write_q <= 1'b0; lock_q <= 1'b0;
                    protocol_error <= 1'b0;
                end else begin
                    if (completion_valid && !completion_ready)
                        protocol_error <= 1'b1;
                    if (response_fire && published_q) begin
                        published_q <= 1'b0;
                        captured_q <= 1'b0;
                    end
                    if (command_fire) issued_q <= 1'b1;
                    if (physical_capture) begin
                        captured_q <= 1'b1;
                        response_q <= completion_data;
                    end
                    if (active_q && !canceled_q && cpu_boundary && state_q == TS)
                        state_q <= TC;
                    if (logical_complete) begin
                        active_q <= 1'b0; issued_q <= 1'b0; state_q <= IDLE;
                        published_q <= !response_ready;
                        captured_q <= !response_ready;
                    end
                    if (canceled_q && result_available) begin
                        active_q <= 1'b0; issued_q <= 1'b0; canceled_q <= 1'b0;
                        captured_q <= 1'b0; state_q <= IDLE;
                    end
                    if (cancel) begin
                        published_q <= 1'b0; state_q <= IDLE;
                        if (active_q && issued_q && !result_available)
                            canceled_q <= 1'b1;
                        else begin
                            active_q <= 1'b0; issued_q <= 1'b0; canceled_q <= 1'b0;
                            captured_q <= 1'b0;
                        end
                    end
                    // Packet callers may present the NEXT request at the same
                    // boundary as completion, so back-to-back Ts/Tc has no Ti.
                    // A level-held CPU bus needs an admission shim, not replay.
                    if (request_fire) begin
                        active_q <= 1'b1; issued_q <= 1'b0; canceled_q <= 1'b0;
                        captured_q <= 1'b0; published_q <= 1'b0; state_q <= TS;
                        address_q <= request_address; data_q <= request_data;
                        lanes_q <= request_lanes; class_q <= request_class;
                        write_q <= request_write; lock_q <= request_lock;
                    end
                end
            end
        end else begin : maximum
            // Static wire bypass; retention is the endpoint's existing contract.
            assign request_ready = !reset && !cancel && command_accept;
            assign command_valid = !reset && !cancel && request_valid;
            assign command_address = request_address;
            assign command_data = request_data;
            assign command_lanes = request_lanes;
            assign command_class = request_class;
            assign command_write = request_write;
            assign command_lock = request_lock;
            assign completion_ready = !reset && !cancel && response_ready;
            assign response_valid = !reset && !cancel && completion_valid;
            assign response_data = completion_data;
            assign physical_capture = completion_valid && completion_ready;
            assign logical_complete = physical_capture;
            assign external_wait = 1'b0; assign deadline_miss = 1'b0;
            assign busy = 1'b0; assign draining = 1'b0;
            assign protocol_error = 1'b0; assign logical_state = 2'd0;
        end
    endgenerate
endmodule
