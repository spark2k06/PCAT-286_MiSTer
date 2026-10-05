// Preserve target bytes read only for historical length qualification. Preview
// is not an architectural queue consumption: IP/prefix state advance on replay.
`ifndef SPK286_TARGET_REPLAY_SV
`define SPK286_TARGET_REPLAY_SV
`timescale 1ns/1ps
module spk286_target_replay (
    input logic clk, reset, cancel, start,
    input logic capture,
    input logic [7:0] capture_data,
    input logic consume,
    output logic valid,
    output logic [7:0] data,
    output logic [3:0] count
);
    logic [7:0] bytes_q [0:9];
    logic [3:0] write_q, read_q;
    assign count = write_q - read_q;
    assign valid = write_q != read_q;
    assign data = valid ? bytes_q[read_q] : 8'd0;
    always_ff @(posedge clk) begin
        if (reset || cancel || start) begin
            write_q <= 4'd0;
            read_q <= 4'd0;
        end else begin
            if (capture && write_q < 4'd10) begin
                bytes_q[write_q] <= capture_data;
                write_q <= write_q + 4'd1;
            end
            if (consume && valid) read_q <= read_q + 4'd1;
        end
    end
endmodule
`endif
