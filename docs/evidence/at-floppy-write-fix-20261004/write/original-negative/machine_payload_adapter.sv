`timescale 1ns/1ps
module spk286_at_dma_read_payload_adapter (
 input logic clk, reset, dma_transfer_valid,
 input logic [2:0] dma_active_channel,
 input logic [1:0] dma_transfer_byte_enable,
 input logic dma_transfer_read_from_memory, dma_memory_response_valid, dma_transfer_complete,
 input logic [15:0] dma_memory_data_in,
 output wire [15:0] dma_endpoint_data
);
assign dma_endpoint_data = (dma_active_channel < 3'd4) &&
                                 dma_transfer_byte_enable[1] ?
                                 {8'h00, dma_memory_data_in[15:8]} :
                                 dma_memory_data_in;

endmodule
