// Private M6f serialized memory WRITE qualification on the M6e phases.
// No new payload/response slot: write_q/address_q/write_data_q stay original.
    generate
        if (P06_WRITE_TIMING && (!P06_DATA_TIMING || !P06_SHARED_TIMING)) begin : p06_invalid_write_configuration
            initial $fatal(1, "M6f WRITE requires DATA and SHARED timing");
        end
    endgenerate
    /* verilator lint_off UNUSEDSIGNAL */
    wire p06_read_cycle = !P06_WRITE_TIMING || !write_q;
    /* verilator lint_on UNUSEDSIGNAL */
