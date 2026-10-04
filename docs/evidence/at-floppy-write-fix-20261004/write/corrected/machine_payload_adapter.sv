`timescale 1ns/1ps
module spk286_at_dma_read_payload_adapter (
 input logic clk, reset, dma_transfer_valid,
 input logic [2:0] dma_active_channel,
 input logic [1:0] dma_transfer_byte_enable,
 input logic dma_transfer_read_from_memory, dma_memory_response_valid, dma_transfer_complete,
 input logic [15:0] dma_memory_data_in,
 output wire [15:0] dma_endpoint_data
);
    // DMA1 byte devices consume the addressed lane in the low byte. Retain
    // that selection with the response: the registered completion pulse is
    // consumed one edge later, after memory data expires and the DMA address
    // (and therefore its byte lane) advances. SoundBlaster still consumes the
    // live response while dma_memory_response_valid is asserted.
    wire [15:0] dma_read_lane_data = (dma_active_channel < 3'd4) &&
                                    dma_transfer_byte_enable[1] ?
                                    {8'h00, dma_memory_data_in[15:8]} :
                                    dma_memory_data_in;
    logic [15:0] dma_read_payload_q;
    always_ff @(posedge clk) begin
        if (reset)
            dma_read_payload_q <= 16'h0000;
        else if (dma_transfer_valid && dma_transfer_read_from_memory &&
                 dma_memory_response_valid)
            dma_read_payload_q <= dma_read_lane_data;
    end
    assign dma_endpoint_data = dma_transfer_complete &&
                                   dma_transfer_read_from_memory ?
                                   dma_read_payload_q : dma_read_lane_data;
    
endmodule
