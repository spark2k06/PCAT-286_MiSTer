`timescale 1ns/1ps

module spk286_diag_monitor_tb;
    logic clk = 1'b0;
    logic reset = 1'b1;
    logic accepted_io_write = 1'b0;
    logic [15:0] port_address = 16'h0000;
    logic [7:0] write_data = 8'h00;
    wire diagnostic_pass;
    wire diagnostic_failure;
    wire [2:0] progress;

    always #5 clk = ~clk;

    spk286_diag_monitor dut (.*);

    task automatic write_port(input logic [15:0] port_value,
                              input logic [7:0] data_value);
        begin
            @(negedge clk);
            port_address = port_value;
            write_data = data_value;
            accepted_io_write = 1'b1;
            @(negedge clk);
            accepted_io_write = 1'b0;
        end
    endtask

    initial begin
        repeat (3) @(posedge clk);
        reset = 1'b0;

        write_port(16'h1234, 8'h70);
        if (progress != 0)
            $fatal(1, "non-diagnostic port advanced progress");

        write_port(16'h0080, 8'h70);
        write_port(16'h0080, 8'h72);
        write_port(16'h0080, 8'hff);
        if (progress != 0 || diagnostic_pass)
            $fatal(1, "wrong marker did not reset progress");

        write_port(16'h0080, 8'h70);
        write_port(16'h0080, 8'h72);
        write_port(16'h0080, 8'h71);
        write_port(16'h0080, 8'h86);
        if (!diagnostic_pass || diagnostic_failure || progress != 4)
            $fatal(1, "passing marker sequence was not recognized");

        write_port(16'h0081, 8'he6);
        if (!diagnostic_pass || !diagnostic_failure)
            $fatal(1, "diagnostic failure was not latched independently");

        reset = 1'b1;
        @(posedge clk);
        #1;
        if (diagnostic_pass || diagnostic_failure || progress != 0)
            $fatal(1, "reset did not clear diagnostic observations");

        $display("I4_DIAG_MONITOR_PASS checks=5");
        $finish;
    end
endmodule
